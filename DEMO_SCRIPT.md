# Demo script: 15 minutes, live demo plus slides

**Audience:** Primark CXO and board.
**Goal:** they leave believing three things. (1) There is real money sitting with customers who are quietly leaving. (2) We can see who they are and what to do. (3) The numbers can be trusted.
**Say early and say plainly:** all data is synthetic, modelled on Primark-style behaviour. Real data would replace it.

Read numbers off the screen rather than from this page. They shift slightly each time the models are re-run. The figures in brackets are typical values to expect.

---

## Run of show

| Min | Part | On screen | Purpose |
|---|---|---|---|
| 0:00 to 1:00 | Open | Slide 1 to 2 | The question and the disclosure |
| 1:00 to 3:30 | The problem and the idea | Slides 3 to 5 | Why this matters, how it works in one sentence |
| 3:30 to 5:00 | The headline | Live: Overview | One number, then where it sits |
| 5:00 to 6:30 | The plan | Live: Segments | Four groups, four plays |
| 6:30 to 9:30 | One customer | Live: Customer C10000 | The story that makes it real |
| 9:30 to 11:30 | The programme | Live: Loyalty | What more members is worth |
| 11:30 to 13:00 | Trust | Live: Model | Tested on a year it never saw |
| 13:00 to 14:30 | Close | Slides 9 to 11 | Decision and next steps |
| 14:30 to 15:00 | Buffer | | Questions |

If you are running long, drop the Loyalty section to 60 seconds (just the sliders) and keep everything else.

---

## Before you start (5 minutes before)

1. Terminal: `uvicorn api.main:app --reload`. Open http://127.0.0.1:8000 in a clean browser window.
2. Set the theme you want on the projector. Light is the default and works best in a bright room.
3. Zoom the browser to 110% or 125% for the back of the room.
4. Click **Overview** once so the first load is cached. Click **C10000** once as well.
5. Have the slide deck open in a second window. Turn off notifications.
6. Backup: slides 7 and 8 carry the four groups and the evidence if the laptop misbehaves. Also export the deck to PDF and keep it on the desktop.

---

## 0:00 to 1:00, Open (slides 1 and 2)

**Say:**
"Every customer you can identify through the app and loyalty card is worth something over the next year. Some of them have quietly stopped coming and nobody has noticed. I want to show you how much value that is, who they are, and what to do about it. One thing up front: everything you will see is synthetic data, built to behave like Primark shoppers in the UK and Ireland. There is a badge at the top of every screen saying so."

## 1:00 to 3:30, The problem and the idea (slides 3 to 5)

**Say:**
"Today we know what customers spent. We do not know who is about to stop. A customer who used to visit every three weeks and has not been seen for three months looks the same in a sales report as one who is simply busy."

"The idea in one sentence: for every customer, estimate the chance they are still with us, and how much they will spend if they are, then multiply. Two methods do that. A survival-style model estimates the chance they are still active and how many visits to expect. Gradient boosting estimates what they spend per visit. We compare the answer with the standard RFM method, on a year the model never saw."

Keep slides 3 to 5 under 2.5 minutes. Do not explain BG/NBD by name unless asked.

## 3:30 to 5:00, The headline (live: Overview)

**Click:** Overview. Let the big number settle.

**Say:**
"This is the headline. Over the next 12 months, about [the figure on screen] of revenue sits with customers the model thinks may already be drifting away. Of that, targeted campaigns could realistically win back the figure shown under it. That rests on assumptions, so it carries the label."

**Click:** drag the **Protect** slider from 20% to 30%, then back. Then the **Win back** slider.

**Say:**
"These are the assumptions, and you can move them. Protect is set at a 20% save rate, Win back at 12%. Drag them and the recoverable figure and the net return after campaign cost move with them. If you believe more, it climbs. If you believe less, it falls, and it is still positive. The point of the pilot is to replace these two numbers with measured ones."

**Click:** the **Customers** switch on the bar. Then back to **Revenue at risk**.

**Say:**
"Same bar, two views. By customers, half of them are in the blue group. By money, blue is under half of the risk and the orange group is almost a third. A small group of high-value customers carries far more of the risk than their numbers suggest. That is where we start."

**Click:** the **Protect** tile.

## 5:00 to 6:30, The plan (live: Segments)

**Say:**
"Every customer is placed on two questions: how much are they worth if we keep them, and how likely are they to have drifted? That gives four groups, each with its own play."

Point to each tile, one sentence each:
- **Protect:** "high value and slipping. Personal outreach before they lapse."
- **Grow:** "high value and healthy. Reward them, do not discount."
- **Win back:** "lower value and probably gone. Cheap email, nothing expensive."
- **Maintain:** "lower value, still active. Leave them alone."

**Click:** the **Protect** priority table. Point at the economics box.
"Here is the working behind the recoverable figure: a share of customers we keep, a cost to contact, a cost of the offer. Primark's own campaign data replaces these assumptions."

**Click:** the first row, or type **C10000** into Customer lookup.

## 6:30 to 9:30, One customer (live: Customer C10000)

This is the centrepiece. Slow down.

**Say:**
"This is C10000: 38, Manchester, a loyal family shopper. Fifty visits, about £1,900 spent, a loyalty member with the app."

Point to the summary box.
"The model says there is only a [27%] chance she is still an active customer. She is worth about [£350] over the next year if we keep her, but expected value today is only about [£95]. About [£260] is at risk."

Point to **Why this customer was flagged**.
"The model explains itself in plain English. Last visit 102 days ago, five times her usual gap of 20 days."

Point to the **still active?** chart.
"Each tick along the bottom is a visit. After every visit the chance she is still with us jumps back up, then fades while she is away. After her last visit in June the line drops through the 50% line and keeps falling."

Point to **Days between visits**.
"This is what the model noticed. Her gaps were steady at about 20 days, then 26, 31, 38, 60. The bars turn orange when a gap is more than one and a half times her usual."

Point to **Recommended next step**.
"The action: member early access plus an offer on womenswear, her favourite category, through app push and email. One customer, one reason, one next step."

**Optional (if time):** open another Protect customer from the list to show it is not a one-off.

## 9:30 to 11:30, The programme (live: Loyalty)

**Say:**
"Members visit about 18% more often and are about 18% less likely to leave after a visit. I want to be careful here. Keen shoppers are the ones who join, so this is an association, not proof the programme causes it."

**Click:** drag the **share of the gap the programme really causes** slider to 25%, then back to 50%.
"You decide how much you believe. At 50%, enrolling the best 20% of non-members first returns about [2.5 pounds for every pound spent]."

**Click:** **Random customers**.
"Enrolling at random is far worse. Who you enrol matters more than how many."

**Click:** back to **Best customers first**. Point at the peak of the curve.
"There is a sweet spot. Past it, you are paying to enrol customers who would not have changed their behaviour."

## 11:30 to 13:00, Trust (live: Model)

**Say:**
"Can we trust it? We tested it on a full year it never saw."

Point to the strip numbers:
- "The average miss per customer is about [£38]. The standard RFM method, the usual marketing rule of thumb, misses by about [£42]. So we are about 10 percent better. I will be straight about that: it is a modest gain, not a miracle."
- "Total forecast against what really happened is within a few percent. A naive 'same as before' forecast overshoots by more than 150%, which is why we compare against RFM."
- "Churn detection scores [0.85], where 0.5 is a coin flip and 1.0 is perfect. Recency alone gets about 0.83."

Scroll to the **scorecard ladder**.
"Each row adds one idea. Baseline, then the RFM method, then boosting alone, then the visit model, then the combinations, then the final blend. Boosting alone is already close to the final on average miss. What the visit model adds is the chance a customer has already gone, and the split of value into expected and at risk. Boosting alone cannot tell you who is quietly leaving. We chose the blend because it gets the total right to within about 1 percent, while the single boosting models under-forecast the total by around 9 to 10 percent."

Point to the **forecast vs reality** chart.
"Predicted and actual track each other across all ten groups of customers, highest value to lowest."

Point to **Did the visit model learn the truth?**
"Because the data is synthetic, we know the real settings that produced it. The model, never shown them, lands close. That is a check you can only do with synthetic data."

## 13:00 to 14:30, Close (slides 9 to 11)

**Say:**
"Three things. Value at risk is large and concentrated in a small group of high-value customers. We can see who they are, why, and what to do. And the numbers hold up on a year the model never saw."

"What we need from Primark to make this real: a month of real identified-customer data, one campaign test to replace our assumptions with measured save rates, and a decision on which segment to pilot first. I would pilot Protect: it has the most money per customer and the clearest action."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Page shows "Something went wrong" | The server stopped. Tab to the terminal, rerun `uvicorn api.main:app --reload`, refresh. Say "give me ten seconds" and carry on |
| Laptop fails entirely | Switch to the screenshots at the end of the deck and narrate the same path |
| Number on screen differs from this script | Use the screen. Say nothing about it |
| Projector washes out light theme | Click the theme switch for dark |

---

## Likely questions, with honest answers

**"Is this real data?"** No. It is synthetic and labelled so on every screen. It is built to behave like Primark shoppers so we can show the method. Real data would use the same five tables.

**"How do you know it would work on our customers?"** We do not yet. The test on a held-out year shows the method recovers the truth when the world behaves the way the model assumes. The real test is a pilot on Primark data.

**"Where does the recoverable figure come from?"** From assumed save rates, contact costs and offer costs for each segment, shown on the Segments page and adjustable with the sliders on the Overview. Protect is 20 percent, Win back 12 percent. They are placeholders. A single campaign test would replace them with measured figures.

**"What about customers you cannot identify?"** They are not in the data. This covers shoppers identified through the app, loyalty card or email. That is a limit worth stating.

**"Does the loyalty programme really cause higher spend?"** We cannot say from this data. Members may simply be keener shoppers. That is why the simulator lets you choose how much of the gap you believe the programme causes.

**"Why not just use one big machine learning model?"** On spend alone, boosting by itself is nearly as accurate as our final blend, and the scorecard shows that openly. We keep the visit model because it answers a different question: the chance a customer has already left, which boosting cannot give. The blend also keeps the total forecast within about 1 percent, where boosting alone runs 9 to 10 percent low.

**"Why a blend rather than the best single model?"** Per customer, stacked is slightly closer. For budgeting, the total matters, and the blend gets that right. We chose it for that reason and we say so.

**"How often would it update?"** The pipeline runs in about a minute on a laptop. A weekly refresh is realistic.

**"What would it cost to do this for real?"** Not answered by this demo. Say you will come back with a scoped estimate.

**"Is gender or age driving the decisions?"** They are currently inputs to the spend model. We would remove or review them before real use, and the model should be checked for fairness across groups. That is on the list.

**"How sure are you about a single prediction?"** The demo shows a point estimate, not a range. An uncertainty range per customer is a planned addition.

**"Does this use an LLM?"** Not yet. The numbers come from statistical models, so they are repeatable. We plan to add an LLM only to phrase a customer briefing and a draft message, never to calculate, with a person approving every message.
