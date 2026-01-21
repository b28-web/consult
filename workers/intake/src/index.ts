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

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // Health check
    if (path === "/health") {
      return new Response("ok", { status: 200 });
    }

    // Route: /intake/{client_slug}/{channel}
    const match = path.match(/^\/intake\/([a-z0-9-]+)\/(form|sms|voice)$/);
    if (!match) {
      return new Response("Not Found", { status: 404 });
    }

    const [, clientSlug, channel] = match;

    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    try {
      switch (channel) {
        case "form":
          return await handleFormSubmission(request, env, clientSlug);
        case "sms":
          return await handleSmsWebhook(request, env, clientSlug);
        case "voice":
          return await handleVoiceWebhook(request, env, clientSlug);
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

  if (contentType.includes("application/json")) {
    data = await request.json();
  } else {
    const formData = await request.formData();
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

  // Basic validation
  if (!data.name || !data.email || !data.message) {
    return new Response(
      JSON.stringify({ error: "Name, email, and message are required" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  // Honeypot check (spam prevention)
  const formData = await request.clone().formData().catch(() => null);
  if (formData?.get("website")) {
    // Bot detected, silently accept but don't process
    return new Response(
      JSON.stringify({
        submission_id: crypto.randomUUID(),
        message: "Thank you, we'll be in touch soon.",
      }),
      { status: 202, headers: { "Content-Type": "application/json" } }
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
  request: Request,
  env: Env,
  clientSlug: string
): Promise<Response> {
  // TODO: Validate Twilio signature
  // const signature = request.headers.get("X-Twilio-Signature");

  const formData = await request.formData();
  const payload = Object.fromEntries(formData.entries());

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
  env: Env,
  clientSlug: string
): Promise<Response> {
  // TODO: Validate Twilio signature

  const formData = await request.formData();
  const payload = Object.fromEntries(formData.entries());

  const submissionId = crypto.randomUUID();

  await writeSubmission(env, {
    id: submissionId,
    client_slug: clientSlug,
    channel: "voicemail",
    payload,
    source_url: "",
  });

  // Return TwiML for voicemail
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Please leave a message after the beep.</Say>
  <Record maxLength="120" transcribe="true" />
</Response>`,
    {
      status: 200,
      headers: { "Content-Type": "application/xml" },
    }
  );
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
    INSERT INTO inbox_submission (id, client_slug, channel, payload, source_url, created_at)
    VALUES (
      ${submission.id}::uuid,
      ${submission.client_slug},
      ${submission.channel},
      ${JSON.stringify(submission.payload)}::jsonb,
      ${submission.source_url},
      NOW()
    )
  `;
}
