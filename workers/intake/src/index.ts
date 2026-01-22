/**
 * Intake Worker
 *
 * Fast edge handler for all inbound submissions:
 * - Web form submissions
 * - Twilio SMS webhooks
 * - Twilio voice/voicemail webhooks
 *
 * Design goal: < 50ms response, minimal processing.
 * Writes raw submission to Postgres, Django processes later.
 */

import { neon } from "@neondatabase/serverless";

interface Env {
  // From Doppler
  NEON_DATABASE_URL: string;
  INTAKE_API_KEY: string;
  TWILIO_AUTH_TOKEN?: string;
}

interface FormSubmission {
  name: string;
  email: string;
  phone?: string;
  service?: string;
  message: string;
  source_url: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
}

interface SmsPayload {
  from: string;
  to: string;
  body: string;
  message_sid: string;
  media_urls: string[];
  num_media: number;
}

interface VoicemailPayload {
  call_sid: string;
  from: string;
  to: string;
  recording_url: string;
  recording_sid: string;
  recording_duration: number;
  transcription_text: string;
  transcription_status: string;
}

/**
 * Validate Twilio webhook signature using Web Crypto API.
 *
 * Twilio signs requests with HMAC-SHA1:
 * 1. Concatenate request URL + sorted POST params (key + value pairs)
 * 2. HMAC-SHA1 with auth token
 * 3. Base64 encode result
 * 4. Compare with X-Twilio-Signature header
 */
async function validateTwilioSignature(
  authToken: string,
  signature: string,
  url: string,
  params: Record<string, string>
): Promise<boolean> {
  // Build the data string: URL + sorted params concatenated
  const sortedKeys = Object.keys(params).sort();
  const paramString = sortedKeys.map((key) => key + params[key]).join("");
  const data = url + paramString;

  // Create HMAC-SHA1 signature using Web Crypto API
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(authToken),
    { name: "HMAC", hash: "SHA-1" },
    false,
    ["sign"]
  );

  const signatureBuffer = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(data)
  );

  // Convert to base64
  const expectedSignature = btoa(
    String.fromCharCode(...new Uint8Array(signatureBuffer))
  );

  return signature === expectedSignature;
}

/**
 * Validate Twilio signature for a request. Returns error response if invalid.
 */
async function requireTwilioSignature(
  request: Request,
  env: Env,
  formData: FormData
): Promise<Response | null> {
  // Skip validation if no auth token configured (dev mode)
  if (!env.TWILIO_AUTH_TOKEN) {
    console.warn("TWILIO_AUTH_TOKEN not set, skipping signature validation");
    return null;
  }

  const signature = request.headers.get("X-Twilio-Signature");
  if (!signature) {
    console.error("Missing X-Twilio-Signature header");
    return new Response("Forbidden", { status: 403 });
  }

  // Convert FormData to Record for validation
  const params: Record<string, string> = {};
  for (const [key, value] of formData.entries()) {
    params[key] = value.toString();
  }

  // Use the full request URL for validation
  const url = request.url;

  const isValid = await validateTwilioSignature(
    env.TWILIO_AUTH_TOKEN,
    signature,
    url,
    params
  );

  if (!isValid) {
    console.error("Invalid Twilio signature");
    return new Response("Forbidden", { status: 403 });
  }

  return null; // Signature valid
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // Health check
    if (path === "/health") {
      return new Response("ok", { status: 200 });
    }

    // Route: /intake/{client_slug}/{channel}
    const match = path.match(
      /^\/intake\/([a-z0-9-]+)\/(form|sms|voice|voice-complete|voice-transcription)$/
    );
    if (!match) {
      return new Response("Not Found", { status: 404 });
    }

    const [, clientSlug, channel] = match;

    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    try {
      // Form submissions don't need Twilio validation
      if (channel === "form") {
        return await handleFormSubmission(request, env, clientSlug);
      }

      // All Twilio webhooks need signature validation
      // Parse FormData once and pass to handlers
      const formData = await request.formData();

      const validationError = await requireTwilioSignature(request, env, formData);
      if (validationError) {
        return validationError;
      }

      switch (channel) {
        case "sms":
          return await handleSmsWebhook(env, clientSlug, formData);
        case "voice":
          return await handleVoiceWebhook(request, clientSlug);
        case "voice-complete":
          return await handleVoiceRecordingComplete(env, clientSlug, formData);
        case "voice-transcription":
          return await handleVoiceTranscription(env, clientSlug, formData);
        default:
          return new Response("Unknown channel", { status: 400 });
      }
    } catch (error) {
      console.error("Intake error:", error);
      return new Response("Internal Server Error", { status: 500 });
    }
  },
};

async function handleFormSubmission(
  request: Request,
  env: Env,
  clientSlug: string
): Promise<Response> {
  // Parse form data (supports both JSON and form-urlencoded)
  const contentType = request.headers.get("content-type") || "";
  let data: FormSubmission;
  let honeypotTriggered = false;

  if (contentType.includes("application/json")) {
    data = await request.json();
    // Check honeypot field for JSON requests
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    honeypotTriggered = !!(data as any).website;
  } else {
    const formData = await request.formData();
    // Check honeypot field for form requests
    honeypotTriggered = !!formData.get("website");
    data = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      phone: (formData.get("phone") as string) || undefined,
      service: (formData.get("service") as string) || undefined,
      message: formData.get("message") as string,
      source_url: formData.get("source_url") as string,
      utm_source: (formData.get("utm_source") as string) || undefined,
      utm_medium: (formData.get("utm_medium") as string) || undefined,
      utm_campaign: (formData.get("utm_campaign") as string) || undefined,
    };
  }

  // Honeypot check (spam prevention)
  if (honeypotTriggered) {
    // Bot detected, silently accept but don't process
    return new Response(
      JSON.stringify({
        submission_id: crypto.randomUUID(),
        message: "Thank you, we'll be in touch soon.",
      }),
      { status: 202, headers: { "Content-Type": "application/json" } }
    );
  }

  // Basic validation
  if (!data.name || !data.email || !data.message) {
    return new Response(
      JSON.stringify({ error: "Name, email, and message are required" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  // Generate submission ID
  const submissionId = crypto.randomUUID();

  // Write to database
  await writeSubmission(env, {
    id: submissionId,
    client_slug: clientSlug,
    channel: "form",
    payload: data,
    source_url: data.source_url || "",
  });

  // Return success
  return new Response(
    JSON.stringify({
      submission_id: submissionId,
      message: "Thank you, we'll be in touch soon.",
    }),
    {
      status: 202,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*", // CORS for Astro sites
      },
    }
  );
}

async function handleSmsWebhook(
  env: Env,
  clientSlug: string,
  formData: FormData
): Promise<Response> {
  // Extract standard Twilio SMS fields
  const from = (formData.get("From") as string) || "";
  const to = (formData.get("To") as string) || "";
  const body = (formData.get("Body") as string) || "";
  const messageSid = (formData.get("MessageSid") as string) || "";
  const numMedia = parseInt((formData.get("NumMedia") as string) || "0", 10);

  // Extract MMS media URLs (MediaUrl0, MediaUrl1, etc.)
  const mediaUrls: string[] = [];
  for (let i = 0; i < numMedia; i++) {
    const mediaUrl = formData.get(`MediaUrl${i}`) as string;
    if (mediaUrl) {
      mediaUrls.push(mediaUrl);
    }
  }

  const payload: SmsPayload = {
    from,
    to,
    body,
    message_sid: messageSid,
    media_urls: mediaUrls,
    num_media: numMedia,
  };

  const submissionId = crypto.randomUUID();

  await writeSubmission(env, {
    id: submissionId,
    client_slug: clientSlug,
    channel: "sms",
    payload,
    source_url: "",
  });

  // Twilio expects TwiML response (empty = no auto-reply)
  return new Response(
    '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    {
      status: 200,
      headers: { "Content-Type": "application/xml" },
    }
  );
}

async function handleVoiceWebhook(
  request: Request,
  clientSlug: string
): Promise<Response> {
  // Initial voice call - just return TwiML prompt, no submission yet
  // Submission is created when recording completes (voice-complete callback)
  const baseUrl = new URL(request.url).origin;

  // Return TwiML for voicemail with callbacks
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Please leave a message after the beep.</Say>
  <Record maxLength="120" transcribe="true"
          action="${baseUrl}/intake/${clientSlug}/voice-complete"
          transcribeCallback="${baseUrl}/intake/${clientSlug}/voice-transcription" />
</Response>`,
    {
      status: 200,
      headers: { "Content-Type": "application/xml" },
    }
  );
}

async function handleVoiceRecordingComplete(
  env: Env,
  clientSlug: string,
  formData: FormData
): Promise<Response> {
  // Extract Twilio recording callback fields
  const callSid = (formData.get("CallSid") as string) || "";
  const from = (formData.get("From") as string) || "";
  const to = (formData.get("To") as string) || "";
  const recordingUrl = (formData.get("RecordingUrl") as string) || "";
  const recordingSid = (formData.get("RecordingSid") as string) || "";
  const recordingDuration = parseInt(
    (formData.get("RecordingDuration") as string) || "0",
    10
  );

  const payload: VoicemailPayload = {
    call_sid: callSid,
    from,
    to,
    recording_url: recordingUrl,
    recording_sid: recordingSid,
    recording_duration: recordingDuration,
    transcription_text: "", // Will be updated by transcription callback
    transcription_status: "pending",
  };

  const submissionId = crypto.randomUUID();

  await writeSubmission(env, {
    id: submissionId,
    client_slug: clientSlug,
    channel: "voicemail",
    payload,
    source_url: "",
  });

  // Return empty TwiML (call will end after recording)
  return new Response(
    '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    {
      status: 200,
      headers: { "Content-Type": "application/xml" },
    }
  );
}

async function handleVoiceTranscription(
  env: Env,
  clientSlug: string,
  formData: FormData
): Promise<Response> {
  // Extract transcription fields
  const recordingSid = (formData.get("RecordingSid") as string) || "";
  const transcriptionText = (formData.get("TranscriptionText") as string) || "";
  const transcriptionStatus =
    (formData.get("TranscriptionStatus") as string) || "";

  if (!recordingSid) {
    console.error("Transcription callback missing RecordingSid");
    return new Response("OK", { status: 200 });
  }

  // Update existing submission's payload with transcription
  // Find by recording_sid in payload
  const sql = neon(env.NEON_DATABASE_URL);

  await sql`
    UPDATE inbox_submission
    SET payload = payload || ${JSON.stringify({
      transcription_text: transcriptionText,
      transcription_status: transcriptionStatus,
    })}::jsonb
    WHERE client_slug = ${clientSlug}
      AND channel = 'voicemail'
      AND payload->>'recording_sid' = ${recordingSid}
      AND processed_at IS NULL
  `;

  // Also update any already-processed messages
  // (transcription can arrive after processing)
  await sql`
    UPDATE inbox_message
    SET body = ${transcriptionText}
    FROM inbox_submission s
    WHERE inbox_message.id = s.message_id
      AND s.client_slug = ${clientSlug}
      AND s.channel = 'voicemail'
      AND s.payload->>'recording_sid' = ${recordingSid}
      AND ${transcriptionText} != ''
  `;

  return new Response("OK", { status: 200 });
}

interface SubmissionRecord {
  id: string;
  client_slug: string;
  channel: string;
  payload: unknown;
  source_url: string;
}

async function writeSubmission(env: Env, submission: SubmissionRecord): Promise<void> {
  const sql = neon(env.NEON_DATABASE_URL);

  await sql`
    INSERT INTO inbox_submission (id, client_slug, channel, payload, source_url, created_at, error)
    VALUES (
      ${submission.id}::uuid,
      ${submission.client_slug},
      ${submission.channel},
      ${JSON.stringify(submission.payload)}::jsonb,
      ${submission.source_url},
      NOW(),
      ''
    )
  `;
}
