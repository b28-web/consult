// Message Classification Schema
// Classifies incoming messages from all channels (form, SMS, voicemail, email)

enum MessageCategory {
  QUOTE_REQUEST
  APPOINTMENT_BOOKING
  GENERAL_INQUIRY
  COMPLAINT
  FOLLOW_UP
  SPAM
  OTHER
}

enum MessageIntent {
  WANTS_SERVICE
  WANTS_INFORMATION
  WANTS_STATUS_UPDATE
  WANTS_TO_CANCEL
  WANTS_TO_RESCHEDULE
  PROVIDING_FEEDBACK
  OTHER
}

enum SuggestedAction {
  RESPOND_URGENTLY
  SCHEDULE_CALLBACK
  SEND_QUOTE
  BOOK_APPOINTMENT
  FORWARD_TO_OWNER
  AUTO_REPLY
  MARK_AS_SPAM
  NO_ACTION_NEEDED
}

class MessageClassification {
  is_new_lead bool @description("True if this appears to be a new potential customer")
  urgency int @description("1-5 scale, 5 being most urgent")
  category MessageCategory
  intent MessageIntent
  suggested_action SuggestedAction
  summary string @description("One sentence summary of the message")
  extracted_name string? @description("Contact name if mentioned")
  extracted_phone string? @description("Phone number if mentioned")
  extracted_email string? @description("Email if mentioned")
  extracted_address string? @description("Service address if mentioned")
  confidence float @description("0-1 confidence score for this classification")
}

function ClassifyMessage(
  message_content: string,
  message_source: string,
  client_vertical: string
) -> MessageClassification {
  client GeminiFast
  prompt #"
    You are classifying an incoming message for a {{ client_vertical }} business.

    Message source: {{ message_source }}
    Message content:
    {{ message_content }}

    Classify this message and extract any contact information.
    Consider the business vertical when assessing urgency (e.g., junk hauler leads are often urgent).

    {{ ctx.output_format }}
  "#
}

// Test cases
test new_lead_form_submission {
  functions [ClassifyMessage]
  args {
    message_content #"
      Hi, I need someone to haul away an old couch and some boxes from my garage.
      Can you come by this week? My address is 123 Main St.
      Call me at 555-1234.
      - John
    "#
    message_source "web_form"
    client_vertical "junk_hauler"
  }
}

test appointment_request {
  functions [ClassifyMessage]
  args {
    message_content "I'd like to book a haircut for Saturday afternoon if possible"
    message_source "sms"
    client_vertical "barber"
  }
}

test spam_message {
  functions [ClassifyMessage]
  args {
    message_content "CONGRATULATIONS! You've won a FREE cruise! Click here to claim your prize NOW!!!"
    message_source "email"
    client_vertical "cleaning_company"
  }
}
