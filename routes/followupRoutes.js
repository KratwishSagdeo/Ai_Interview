// ----------------------------------------------------
// Follow-Up Routes
// ----------------------------------------------------
// Defines the routing for the follow-up API endpoint

const express = require("express");
const router = express.Router();

const { handleFollowUp } = require("../controllers/followupController");


// POST /api/followup
router.post("/followup", handleFollowUp);


module.exports = router;
