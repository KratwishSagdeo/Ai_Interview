// ----------------------------------------------------
// Gemini AI Service
// ----------------------------------------------------
// Handles all LLM interactions using Google Gemini API
// Replaces the previous Ollama-based follow-up generator

const { GoogleGenerativeAI } = require("@google/generative-ai");

// ----------------------------------------------------
// Initialize Gemini client
// ----------------------------------------------------

const apiKey = process.env.GEMINI_API_KEY;

if (!apiKey) {
  console.error("FATAL: GEMINI_API_KEY is not set in environment variables.");
  process.exit(1);
}

const genAI = new GoogleGenerativeAI(apiKey);

// Use gemini-1.0-pro
const model = genAI.getGenerativeModel({ model: "gemini-1.0-pro" });


// ----------------------------------------------------
// Generate follow-up interview question
// ----------------------------------------------------

/**
 * Generates a single short follow-up interview question
 * based on the original question and the candidate's answer.
 *
 * @param {string} question - The interview question that was asked
 * @param {string} answer   - The candidate's answer
 * @returns {Promise<string>} - The generated follow-up question
 */
async function generateFollowUp(question, answer) {
  const prompt = `You are an expert technical interviewer conducting a personalized interview.

Your goal is to ask ONE highly relevant follow-up question based strictly on the candidate's answer.

Instructions:
1. Identify the most important concept, keyword, or claim in the candidate's answer.
2. Focus ONLY on that concept.
3. Ask a deeper, more specific question about it.
4. If the answer is shallow → ask for clarification or depth.
5. If the answer is strong → ask a challenging or edge-case question.
6. Do NOT switch topics.
7. Do NOT ask generic or textbook questions.
8. Do NOT repeat the original question.
9. Keep the question under 20 words.
10. Make it feel like a real interviewer probing the candidate.

Context:
Current Question: ${question}
Candidate Answer: ${answer}

Output:
Only return the follow-up question.`;

  try {
    const result = await model.generateContent({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        maxOutputTokens: 80,
      },
    });

    const response = result.response;
    const text = response.text().trim();

    if (!text) {
      return "Can you explain that in more detail?";
    }

    return text;
  } catch (error) {
    // ----------------------------------------------------
    // Handle rate limit (429) errors gracefully
    // ----------------------------------------------------
    if (
      error.status === 429 ||
      error.message?.includes("429") ||
      error.message?.includes("RESOURCE_EXHAUSTED")
    ) {
      console.warn("Gemini rate limit hit. Returning fallback question.");
      return "Can you elaborate on your previous answer?";
    }

    console.error("Gemini API error:", error.message || error);
    return "Can you explain that in more detail?";
  }
}


module.exports = { generateFollowUp };
