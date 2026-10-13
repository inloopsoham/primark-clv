# How the numbers are made

**Speaker:** Soham. Dibyendu adds detail only if asked.
**When:** if the panel asks "where do these numbers come from?", or as a 60-second explanation after the Model page.
**Rule:** say it in this order. Plain words first, the technical name second, and only if someone asks.

---

## The 15-second version

> "We take the customer history Primark already holds. One model works out how likely each customer is to still be shopping with us. A second works out how much they'll spend. Simple arithmetic turns that into pounds at risk, and simple rules turn it into a group and a next step. Then we tested the whole thing on a year it had never seen."

---

## The 60-second version

### 1. What goes in

> "Five tables Primark already has for customers it can identify: who they are, what they bought, what they returned, loyalty, and email. Spend is counted after returns. Today it's 20,000 made-up customers over three years."

**In business terms:** nothing new needs collecting. It runs on data Primark already owns.

*CIO detail:* SQLite and CSV files in, a Python pipeline, no outside connections. A full run takes under a minute on a laptop.

### 2. Facts per customer, frozen at a date

> "For each customer we work out simple facts as of a chosen date: how often they visit, how long since their last visit, how much they spend, what they buy, and whether they return things or open emails. Nothing after that date is ever used."

**In business terms:** it's like judging last year's forecast using only what we knew last year. No peeking at the answer.

*CIO detail:* about 50 measures per customer, built at three dates: one to learn from, one to test on, and one to score today. Technically, this prevents "data leakage".

### 3. Two models, two questions

**Question 1: is she still with us?**
> "The first model learns each customer's normal rhythm. If someone usually shops every three weeks and has now been silent for three months, it becomes much less likely she's still a customer. For C10000, it gives a 27% chance she's still shopping with us, so a 73% chance she has drifted away."

**In business terms:** it's a smart version of the instinct every shop manager has: "We haven't seen her in a while, and that's not like her."

*Technical name:* **BG/NBD**, short for "Beta-Geometric / Negative Binomial Distribution". It's a well-known statistical model, used in retail for over 20 years, that looks at two things only: how often someone buys and how long it's been since their last purchase. It's fitted by "maximum likelihood", which means finding the settings that best explain the history we've seen.

**Question 2: what will she spend?**
> "The second model learns from thousands of past customers what tends to go with higher or lower spending next year: basket size, categories, visit pattern, returns, email engagement. It then applies those lessons to each customer."

**In business terms:** an experienced buyer who has studied every customer's history and can say, "People who shop like this usually spend about this much next year."

*Technical name:* **LightGBM**, a "gradient boosting" model, built and released free by Microsoft. It builds hundreds of small decision trees (simple yes/no questions, such as "Did she visit in the last 90 days?"). Each new tree corrects the mistakes of the ones before. It's one of the most widely used methods for this kind of table-based prediction.

**Putting them together**
> "The final number blends the two models, because together they get the total forecast within about 1% of what actually happened."

**In business terms:** two specialists, one on whether she stays and one on how much she spends, combined into one answer.

### 4. Arithmetic, not AI

> "From there it's simple arithmetic. 'Worth if she stays' is her expected spend divided by the chance she's still active. 'At risk' is that worth multiplied by the chance she's gone. For C10000: £345 × 73% ≈ £253."

**In business terms:** the money we lose if we do nothing about her.

### 5. Rules you can read

> "Two simple rules decide the group. The top 30% by value count as high value, and anyone with more than a 50% chance of having left counts as high risk. The reasons and the next step are written rules based on her own history. The campaign returns assume that 20% of 'Protect' customers and 12% of 'Win back' customers are saved, and we say that openly."

**In business terms:** no hidden logic. A marketing manager could read every rule and change it.

### 6. Proof

> "We trained on older data and asked it to predict a year it had never seen. Its average error was about £38 per customer, against £42 for the standard method most retailers use today. The total forecast was within about 1%. At spotting who will leave, it scores 0.85, where 0.5 would be a coin flip and 1.0 would be perfect."

**In business terms:** we checked it the honest way, against real outcomes it hadn't seen, and it beat the method retailers use today.

*Technical names:*
- The "standard method" is **RFM** (Recency, Frequency, Monetary). It ranks customers by how recently they bought, how often, and how much.
- The 0.85 is the **AUC**: how often the model ranks a customer who left above one who stayed.
- The £38 is the **mean absolute error** (MAE): the average miss per customer, in pounds.

### Close

> "So every number on the screen traces back to a customer's history, a tested model, or an assumption we've labelled. Nothing is a black box, and nothing leaves your systems."

---

## Jargon in plain words

If someone repeats a term back to you, use these lines.

| Term | One-line business meaning |
|---|---|
| Customer Lifetime Value (CLV) | What a customer is expected to spend with us over the next 12 months. |
| BG/NBD | The "is she still with us?" model. It reads how often she shops and how long she's been away. |
| LightGBM / gradient boosting | The "how much will she spend?" model. Hundreds of simple yes/no questions, each one correcting the last. |
| Blend / hybrid | Combining both models into one forecast, because together they're more accurate. |
| Chance she has drifted (churn risk) | The likelihood she has quietly stopped shopping with us. |
| Worth if she stays (potential value) | What she'd spend next year if we keep her. |
| At risk | What we lose if she goes and we do nothing. |
| Snapshot / no data leakage | Only facts known at the time are used, so the test is fair. |
| RFM | The rule of thumb most retailers use today: recent, frequent, big spenders are best. Our benchmark. |
| AUC 0.85 | How good it is at spotting who will leave: 0.5 is guessing, 1.0 is perfect. |
| Mean absolute error (£38) | On average, our spend forecast for a customer is off by about £38. |
| SHAP | A standard way to show which factors pushed one customer's score up or down. Planned next. |
| Save rate (20% / 12%) | Our cautious assumption for how many customers a campaign brings back. To be proven in a pilot. |

---

## If the CIO probes

| Question | Short answer |
|---|---|
| What's the stack? | Python (pandas, SciPy, LightGBM), SQLite, a read-only FastAPI service and a plain JavaScript front end. All open source, so no licences. |
| Where would it run? | As a scheduled batch job on Primark's data platform. It writes scores to a table that the CRM and marketing tools read. |
| How often? | Weekly is realistic. The models are refitted each run, and the RFM benchmark runs alongside them so any drop in accuracy shows up. |
| Is it repeatable? | Yes. With fixed random seeds, the same input gives the same output, and every run saves its scorecard. |
| Does any data leave Primark? | No. There are no external APIs and no LLM calls, and it runs fully offline. |
| How does it scale? | Scoring is a fast batch calculation. Proving it at Primark's full volume is part of the pilot. |
| Can you explain one customer's score? | Yes: her visit rhythm, her silence, and plain-English reasons on screen. Model-level drivers (SHAP) are a planned addition. |
| What's not done yet? | Uncertainty ranges, a review of age and gender as inputs, a log of model versions, and drift monitoring. All are on the list for a pilot. |
