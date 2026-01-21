// BAML Client Configuration
// Using Google Gemini 2.5 for AI tasks

client<llm> Gemini {
  provider google-ai
  options {
    model "gemini-2.5-pro"
    api_key env.GOOGLE_API_KEY
  }
}

client<llm> GeminiFast {
  provider google-ai
  retry_policy Exponential
  options {
    model "gemini-2.5-flash"
    api_key env.GOOGLE_API_KEY
  }
}

// Retry policies
retry_policy Exponential {
  max_retries 2
  strategy {
    type exponential_backoff
    delay_ms 300
    multiplier 1.5
    max_delay_ms 10000
  }
}
