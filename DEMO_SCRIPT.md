# Demo script: 15 minutes, five presenters, one story

**Team:** Rapid Builders
**Audience:** Primark CXO, CIO and a senior AI architect.
**Goal:** they leave believing three things. (1) There is real money with customers who are quietly leaving. (2) We can see who they are and what to do. (3) The numbers can be trusted.
**Say early and plainly:** all data is synthetic, modelled on UK and Ireland shoppers.

Read numbers off the screen, not this page. Bracketed figures are from the reference run.

---

## Who built what

Each presenter shows the part they own, and says so in their first sentence. Before the demo, each person must be able to answer questions on their part (see the Q&A table at the end).

| Presenter | Owns in the framework | Files to know | Presents |
|---|---|---|---|
| **Soham** (product lead) | Product idea, architecture, API and dashboard, campaign economics and sliders | `api/`, `web/`, `run_all.py`, campaign settings in `src/segments.py` | Hook, Overview, Close |
| **Nilanjana** | The synthetic customer world and the customer measures (features) | `src/generate_data.py`, `src/features.py` | The data and the idea |
| **Rima** | The four customer groups and the action for each | Segment rules and actions in `src/segments.py` | Segments |
| **Viditi** | Churn signals, the "why flagged" reasons, and the AI roadmap (LLM briefing and campaign assistant) | `src/segments.py` reasons, Customer page | Customer C10000 |
| **Dibyendu** (ML lead) | Model design and choice, the testing approach and scorecard ladder, the loyalty analysis; technical reviewer for the whole pipeline | `src/models.py`, `src/loyalty.py` | Loyalty and Trust |

Adjust the ownership column so it matches who really did what. Whatever it says, that person must be able to defend it.

---

## Run of show

| Min | Presenter | On screen | Story beat |
|---|---|---|---|
| 0:00 to 1:00 | Soham | Slide 1 (cover) | Two stores, one blind spot |
| 1:00 to 2:30 | Nilanjana | Slides 3 to 5 | What we built it on, and the idea in one sentence |
| 2:30 to 4:30 | Soham | Live: Overview | How big the blind spot is, in pounds |
| 4:30 to 6:00 | Rima | Live: Segments | Four groups, four plays |
| 6:00 to 9:00 | Viditi | Live: Customer C10000 | One customer makes it real |
| 9:00 to 10:30 | Dibyendu | Live: Loyalty | What signing up more members could be worth |
| 10:30 to 12:30 | Dibyendu | Live: Model | Can you trust it? |
| 12:30 to 14:00 | Soham | Slides 9 to 11 | Back to the two stores, and the ask |
| 14:00 to 15:00 | Soham routes questions | | Q&A |

**The story arc:** a question (Soham) → what we built it on (Nilanjana) → how big it is (Soham) → who to act on (Rima) → one real person (Viditi) → a lever to grow it (Dibyendu) → proof (Dibyendu) → the answer to the opening question (Soham).

**Handovers:** every presenter ends with a bridge line that names the next person. Bridges are in bold below. Do not skip them; they are what makes it one story rather than five talks.

**If running long:** cut Loyalty to 45 seconds (one slider, one sentence). Never cut Customer or Model.

---

## Before you start (5 minutes before)

1. Terminal: `uvicorn api.main:app --reload`. Open http://127.0.0.1:8000 in a clean browser window.
2. Light theme. Browser zoom 110% or 125%.
3. Click **Overview** once and **C10000** once so they are cached. Leave the Overview sliders at **Protect 20%, Win back 12%** so the screen matches the leaflet.
4. Deck open in a second window. Notifications off. Deck PDF on the desktop as backup.
5. Stand in speaking order. One clicker or laptop position; each presenter drives their own section.
6. Leaflets: hand out after the close, not before. Full plan in `LEAFLET_SCRIPT.md`.

---

## 0:00 to 1:00, Soham: the hook (slide 1)

Stand away from the laptop. No clicks. Short sentences, pause where marked.

"Primark is opening stores in the United States. On day one, every new store is full. *(pause)*

Back in the UK and Ireland, the stores you have run for years are full too. *(pause)*

Both look like success on a sales report. But neither report can answer the question that decides the next five years: of everyone walking in today, who will still be coming back in twelve months, and who has quietly stopped? *(pause)*

In a new store, you cannot tell a one-off curious visitor from a future regular. In an established store, you cannot tell a busy regular from one who is drifting away. Same blind spot, two sides of the Atlantic.

We are Rapid Builders, and we built something that closes it. Five of us, each showing the part we built, with Dibyendu leading the machine learning."

**Bridge:** "Nilanjana built the world we tested it in."

Rules: ask the question, never claim the US stores have a problem. Do not promise a store-by-store view.

## 1:00 to 2:30, Nilanjana: the data and the idea (slides 3 to 5)

"I built the data. We could not use real Primark customers, so I built 20,000 synthetic ones that behave like UK and Ireland shoppers: how often they visit, what they buy, what they return, whether they use the app. There is a badge on every screen saying it is synthetic.

From their visit history, I worked out a set of simple measures for every customer: how recently they came, how often, how much they spend, their favourite category. Everything after this is built on those measures.

Today a sales report tells you what customers spent. It does not tell you who is about to stop. A customer who visited every three weeks and has not been seen for three months looks the same as one who is simply busy.

The idea in one sentence: for every customer, estimate the chance they are still with us, and what they will spend if they are, then multiply."

**Bridge:** "Soham will show you what that adds up to."

Keep it to 90 seconds. Do not name the models; Dibyendu covers them.

## 2:30 to 4:30, Soham: the headline (live: Overview)

**Click:** Overview. Let the big number settle.

"This is the blind spot, in pounds. Over the next 12 months, about [£540k] of revenue sits with customers who may already be drifting away. Targeted campaigns could win back about [£83.9k]. That carries an 'assumption' label, and here is why."

**Click:** drag **Protect** from 20% to 30%, then back. Then nudge **Win back**.

"These two sliders are the assumptions: what share of at-risk customers a campaign keeps. Protect is set at 20%, Win back at 12%. Nobody has measured these for Primark yet, so we let you move them. Campaign cost is about [£20k], and the net return about [£64k]: roughly three pounds back for every pound spent. Even at half these rates it still pays. A pilot replaces both numbers with measured ones."

**Click:** the **Customers** switch on the bar, then back to **Revenue at risk**.

"By customers, half are in the blue group. By money, a much smaller orange group carries almost a third of the risk. A few high-value customers matter far more than their numbers suggest."

**Bridge:** "Rima built the rules that decide who goes where, and what we do about each."

**Click:** the **Protect** tile.

## 4:30 to 6:00, Rima: the four groups (live: Segments)

Short, fully scripted. One click only.

"I built the customer groups. Every customer gets two questions: how much are they worth if we keep them, and how likely are they to have drifted? That gives four groups, and each gets a different action."

Point to each tile and say one line:
- **Protect:** "High value and slipping. Personal outreach before they lapse."
- **Grow:** "High value and healthy. Reward them, no discounts."
- **Win back:** "Lower value and probably gone. Cheap email, nothing expensive."
- **Maintain:** "Lower value, still active. Leave them alone and save the money."

**Click:** the **Protect** priority table. Point at the first rows.

"The Protect list is ranked by how much money is at risk, so the team always calls the most valuable customers first. Each one comes with a reason and a next step."

**Bridge:** "Viditi will open one of them."

## 6:00 to 9:00, Viditi: one customer (live: Customer C10000)

This is the centrepiece. Slow down.

**Click:** type **C10000** or click the guided-demo shortcut.

"I worked on how the system spots a customer drifting away and explains it in plain English. Meet C10000: 38, Manchester, a family shopper. About fifty visits and £1,900 spent, a member registered on the app."

Point to the summary.
"The model gives her only a [27%] chance of still being an active customer. If we keep her, she is worth about [£345] next year. Expected value today is only [£92], so about [£253] is at risk."

Point to **Why this customer was flagged**.
"Here is the reason, in a sentence anyone can act on: last visit 102 days ago, five times her usual gap of 20 days, and no visits in the last 90."

Point to the **still active?** chart.
"Each tick is a visit. After every visit, the chance she is still with us jumps up, then fades while she is away. After June it falls through the 50% line and keeps falling."

Point to **Days between visits**.
"This is what the system noticed: her gaps were steady at 20 days, then 26, 31, 38, 60. Orange means much longer than her usual."

Point to **Recommended next step**.
"The action: early access plus an offer on womenswear, her favourite category, by app push and email. One customer, one reason, one next step.

Next, we want a language model to turn this page into a short briefing for the CRM team and draft the message. It would never calculate anything, and a person approves every message. That is on our roadmap, not built yet."

**Bridge:** "Dibyendu led the machine learning behind that 27%. He also set the bar for how strictly we test ourselves."

## 9:00 to 10:30, Dibyendu: members (live: Loyalty)

"I led the modelling, so let me start with one lever and then show you how we test everything.

Customers registered as members visit about 18% more often and are about 18% less likely to leave. Primark does not run a classic loyalty card today, so read this as: what could a members programme on the app be worth?

A data scientist's caution here: keen shoppers are the ones who sign up, so this is an association, not proof of cause. Rather than hide that, we built it into the tool."

**Click:** drag **share of the gap the programme really causes** to 25%, then back to 50%.
"You decide how much you believe. At 50%, signing up the best 20% of non-members first returns about [£2.50 per pound spent]."

**Click:** **Random customers**, then back to **Best customers first**.
"Signing up at random does far worse. Who you invite matters more than how many."

## 10:30 to 12:30, Dibyendu: can you trust it? (live: Model)

**Click:** Model.

"When we designed the models, I set one rule: nothing goes on screen unless it beats a simple method on data it has never seen. So we trained on older data and tested on a full year held back."

Point to the strip.
- "Average miss per customer is about [£38]. The standard RFM method, the usual marketing rule of thumb, misses by about [£42]. So we are about 10% better than the method most retailers use today, on a fair, held-out test."
- "The total forecast is within about 1% of what really happened."
- "Spotting who has left scores [0.85], where 0.5 is a coin flip."

Scroll to the **scorecard ladder**.
"I built this ladder so you can see what each idea earns its place for. Each row adds one idea. For spend, gradient boosting does most of the work. The visit model adds something boosting cannot: the probability a customer has already gone, which powers the Protect and Win back lists you just saw. I chose the blend because it gets the total within about 1%, and the total is what a budget is set on."

Point to **Did the visit model learn the truth?**
"And a check you rarely get: because Nilanjana's data is synthetic, we know the hidden settings that produced it. The model was never shown them and recovers them closely."

**Bridge:** "Soham, back to the two stores."

## 12:30 to 14:00, Soham: the close (slides 9 to 11)

"Back to where we started: a new store in the US and an old store in Manchester, with the same blind spot. This closes it.

Three things. Value at risk is large and sits with a small group of high-value customers. We can see who they are, why, and what to do. And, thanks to the testing Dibyendu designed, the numbers hold up on a year the model never saw.

To make it real we need three things from Primark: a sample of real identified-customer data, one campaign test with a control group to replace our assumed save rates, and a decision on which group to start with. We would start with Protect: most money per customer, clearest action."

"Thank you. We are happy to take questions, and each of us will answer on the part we built."

Nilanjana and Rima hand out leaflets now. See `LEAFLET_SCRIPT.md`.

---

## Q&A: who answers what

Business questions: Soham hears them and passes them to the owner by name. Technical and model questions go straight to Dibyendu without routing; he decides whether to answer or invite the owner. If anyone stalls, Dibyendu adds a sentence on technical points, Soham on business points.

| Question | Answered by | Honest answer |
|---|---|---|
| Is this real data? | Nilanjana | No, synthetic and labelled on every screen. Real data would fill the same five tables after a cleaning step. |
| How did you make the data realistic? | Nilanjana | Each customer has their own visit rate, chance of leaving, basket size and favourite category, with seasonality and returns. |
| Are you saying our US stores are underperforming? | Soham | No. We have no data on them. Every new store faces the same question in its first months; this answers it for any shopper you can identify. |
| Could this work for a new US store? | Dibyendu | In principle, yes, for shoppers identified through the app or CRM. The model allows someone to visit once and never return, the typical new-store pattern. It needs a few months of history and is untested on US data. |
| Where does the £83.9k come from? | Soham | Assumed save rates and costs, shown on Segments and adjustable on Overview. At about a quarter of today's rates it breaks even; at half it still pays. A campaign test measures the real rates. |
| How are customers put into groups? | Rima | Two rules: top 30% by value is "high value"; a 50% or higher chance of having drifted is "high risk". |
| Why these actions? | Rima | They are sensible starting rules, not learned from results. A campaign test with a control group tells us which actions really work. |
| How does it explain a customer? | Viditi | Plain-English rules on recency, visit gaps and trend. They are auditable but they are not model attributions; per-customer drivers are a planned upgrade. |
| Does this use an LLM? | Viditi | Not yet. The numbers come from statistical models, so they are repeatable. We plan an LLM only for briefings and draft messages, never for calculation, with human approval. |
| Why not just use gradient boosting? | Dibyendu | For spend accuracy, boosting alone is nearly as good, and we show that. The visit model gives the chance a customer has left, which boosting cannot. |
| Why a blend? | Dibyendu | Per customer, stacked is slightly closer. For budgeting the total matters, and the blend gets that within about 1%. |
| How sure are you about one customer? | Dibyendu | The demo shows a point estimate, not a range. Uncertainty ranges are a planned addition. |
| Are gender and age used? | Dibyendu | Yes, currently as inputs to spend. We would remove or review them, and check fairness, before real use. |
| Does a members programme really cause higher spend? | Dibyendu | We cannot tell from this data. That is why the slider lets you choose. |
| How does it fit our systems? | Soham | Scores run in a batch on Primark's data platform and feed the CRM and marketing tools Primark already uses. It is a scoring layer, not a new marketing platform. |
| How is this different from Salesforce, Optimove or Adobe? | Soham | Those platforms run campaigns; we do not. What we show is a scoring layer Primark owns: value and risk in pounds per customer, accuracy openly tested against simple methods, every assumption visible. It would feed those tools, not replace them. |
| How often would it update? | Soham | The pipeline runs in about a minute on a laptop. Weekly is realistic. |
| What would it cost for real? | Soham | Not answered by this demo. We would come back with a scoped estimate. |

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Page shows "Something went wrong" | Soham restarts `uvicorn api.main:app --reload` and refreshes. The current presenter says "ten seconds" and keeps talking |
| Laptop fails entirely | Switch to the deck PDF and narrate the same path |
| Number on screen differs from this script | Use the screen. Say nothing about it |
| A presenter freezes | The next presenter says their bridge line and carries on. Nobody comments on it |
| Projector washes out light theme | Click the theme switch for dark |
