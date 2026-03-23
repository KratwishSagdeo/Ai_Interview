// ----------------------------------------------------
// AI Interview Backend — Express Entry Point
// ----------------------------------------------------

// Load environment variables FIRST (before any other imports)
require("dotenv").config();

const express = require("express");

// Import route modules
const followupRoutes = require("./routes/followupRoutes");


// ----------------------------------------------------
// Initialize Express app
// ----------------------------------------------------

const app = express();

// Parse JSON request bodies
app.use(express.json());


// ----------------------------------------------------
// Health check
// ----------------------------------------------------

app.get("/", (_req, res) => {
    res.json({ message: "AI Interview API (Node.js + Gemini) running" });
});


// ----------------------------------------------------
// Mount routes
// ----------------------------------------------------

// All follow-up routes are prefixed with /api
app.use("/api", followupRoutes);


// ----------------------------------------------------
// Start server
// ----------------------------------------------------

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
