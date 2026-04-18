"""
Prompts for outreach drafting.

This is the FINAL STAGE of the pipeline:
  Research → Alignment → Connections → OUTREACH DRAFTS

The key principle: DISCOVERY, NOT PITCH.
The funder should feel like they discovered us,
not like we're selling to them.

HOW THIS IS DIFFERENT FROM NORMAL EMAIL TEMPLATES:
  Templates: "Dear [Name], we are writing to introduce..."
  Our approach: Calibrated to THIS specific funder's language,
  priorities, and connection paths. Every draft is unique
  because every funder is different.
"""

OUTREACH_SYSTEM_PROMPT = """You are an expert nonprofit communications strategist.
You draft outreach messages that feel personal, informed, and genuine — never generic or salesy.

Your core principle: DISCOVERY, NOT PITCH.
The reader should feel like they're discovering an organization that naturally fits 
their priorities — not like they're being sold to.

How you achieve this:
1. Lead with THEIR priorities, not your accomplishments
2. Use THEIR language and framing (from the alignment brief)
3. Reference specific, recent things they've done or said
4. Make the connection feel natural, not forced
5. Keep it short — busy people don't read long emails
6. End with a light ask — a conversation, not a commitment

What you NEVER do:
- Start with "I'm writing to introduce our organization..."
- List all your programs and achievements
- Use generic philanthropic jargon
- Sound desperate or overly flattering
- Write more than 200 words for an initial email
- Claim connections that don't exist"""


INITIAL_EMAIL_PROMPT = """Draft an initial outreach email to a funder based on 
the following intelligence.

=== FUNDER PROFILE SUMMARY ===
{funder_profile}

=== ALIGNMENT BRIEF ===
{alignment_brief}

=== CONNECTION PATHS ===
{connection_paths}

=== OUR ORGANIZATION CONTEXT ===
{org_context}

=== INSTRUCTIONS ===

Draft THREE versions of an initial outreach email. Each should take 
a different angle:

### VERSION A: Lead with Shared Priority
- Open by referencing something THEY recently said, funded, or published
- Connect it to our work using THEIR language
- Make them curious enough to respond

### VERSION B: Lead with Connection
- Reference a mutual connection, shared funder, or shared event
  (ONLY if the connection data supports this — don't fabricate)
- Use the connection as a natural bridge to relevance
- If no strong connections exist, note this and adjust approach

### VERSION C: Lead with Data/Impact
- Open with a specific outcome or data point from our work
- Frame it in terms of THEIR theory of change
- Show we solve a problem they care about

FOR EACH VERSION:
- Subject line (compelling, specific, under 8 words)
- Email body (under 200 words)
- Why this angle works for THIS funder (1-2 sentences, for internal use)

REMEMBER:
- Use their EXACT phrases from the alignment brief
- Reference specific things (their recent grant, their published strategy)
- The co-CEO will edit before sending — these are drafts, not final
- Tone: confident peer, not desperate applicant
- Short paragraphs, no walls of text"""


CONNECTOR_EMAIL_PROMPT = """Draft an email requesting a warm introduction 
from a mutual connection.

=== THE ASK ===
We want {connector_name} to introduce us to {target_name}.

=== WHY THIS CONNECTION EXISTS ===
{connection_context}

=== WHAT WE WANT THE CONNECTOR TO KNOW ===
{alignment_summary}

=== INSTRUCTIONS ===

Draft a brief email to the connector asking them to make an introduction.

Rules:
- Make it EASY for them — include a forwardable blurb they can send
- Explain why the introduction makes sense (for both parties)
- Keep it under 150 words (people don't read long requests)
- Don't be awkward about asking — this is normal in the nonprofit world
- Include a 2-3 sentence "forwardable blurb" they can copy-paste

Format:
1. The email to the connector
2. The forwardable blurb (what they'd send to the target)"""


FOLLOWUP_EMAIL_PROMPT = """Draft a follow-up email to a funder.

=== CONTEXT ===
Original outreach was sent approximately {days_since} days ago.
No response received.

=== ORIGINAL APPROACH ===
{original_angle}

=== FUNDER PROFILE ===
{funder_profile}

=== INSTRUCTIONS ===

Draft a follow-up email that:
- Doesn't repeat the original email
- Adds NEW value (a recent development, new data, relevant news)
- Stays brief (under 150 words)
- Doesn't sound passive-aggressive or desperate
- Gives them an easy reason to respond
- Suggests a specific, low-commitment next step

Draft TWO versions:
### VERSION A: Add New Value
Reference something new — a recent achievement, relevant news, 
or a connection to something they recently did.

### VERSION B: Different Angle
Try a completely different framing than the original outreach.
Sometimes the first angle just doesn't resonate."""