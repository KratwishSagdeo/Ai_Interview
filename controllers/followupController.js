// ----------------------------------------------------
// Follow-Up Controller
// ----------------------------------------------------
// Handles the POST /api/followup endpoint
// Validates input and delegates to geminiService

const { generateFollowUp } = require("../services/geminiService");


// ----------------------------------------------------
// POST /api/followup
// ----------------------------------------------------

/**
 * Accepts { question, answer } in the request body.
 * Returns  { followUp } with the AI-generated follow-up question.
 */
async function handleFollowUp(req, res) {
    try {
        const { question, answer } = req.body;

        // --------------------------------------------------
        // Input validation
        // --------------------------------------------------
        if (!question || !answer) {
            return res.status(400).json({
                error: "Both 'question' and 'answer' fields are required.",
            });
        }

        // --------------------------------------------------
        // Generate follow-up via Gemini
        // --------------------------------------------------
        const followUp = await generateFollowUp(question, answer);

        return res.status(200).json({ followUp });
    } catch (error) {
        console.error("Controller error in handleFollowUp:", error.message || error);
        return res.status(500).json({ error: "Internal server error." });
    }
}


module.exports = { handleFollowUp };
