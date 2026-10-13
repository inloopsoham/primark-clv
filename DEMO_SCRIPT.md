# Demo script: 15 minutes, one story

**Team:** Rapid Builders
**Audience:** Primark CXO, CIO and a senior AI architect. Sceptical and cautious.
**The one idea they must leave with:** *Not every customer deserves the same pound.*
**The shape:** one person → two people → everyone → can you trust it → why no LLM → the ask.

Read numbers off the screen, not this page. Bracketed figures are from the reference run.

---

## Who does what

| Person | Role on the day |
|---|---|
| **Viditi** | Main presenter. Drives the laptop from C10000 to the "no LLM" moment. |
| **Soham** | Opens (before and after the film) and closes. Routes business questions in Q&A. Uses `NUMBERS_SCRIPT.md` if asked how the numbers are made. |
| **Dibyendu** | ML lead. The proof (Model page) and one line in the "no LLM" moment. Takes every technical question. |
| **Nilanjana** | Leaflets at the close. Owns data questions in Q&A. |
| **Rima** | Leaflets at the close. Owns segment questions in Q&A. |

Every handover is a fixed line, in **bold**. Nobody steps in anywhere else.

---

## Run of show

| Time | Who | On screen | Beat |
|---|---|---|---|
| 0:00 to 0:20 | Soham | Black, film paused | "Meet one of your customers. Watch." |
| 0:20 to 1:05 | Nobody | Film | Her story |
| 1:05 to 1:25 | Soham | App, already on C10000 | Bridge: "something you can audit" |
| 1:25 to 3:00 | Viditi | C10000 | The film, now as a real screen |
| 3:00 to 4:00 | Viditi | C10001 | Same warning sign, low value |
| 4:00 to 4:40 | Viditi | Comparison panel | Not every customer deserves the same pound |
| 4:40 to 6:40 | Viditi | Overview | Zoom out: now do it for everyone |
| 6:40 to 7:30 | Viditi | Segments | The two customers, at scale |
| 7:30 to 8:15 | Viditi | Loyalty | One lever |
| 8:15 to 10:15 | Dibyendu | Model | The proof |
| 10:15 to 11:15 | Viditi + Dibyendu | Slide 10: Why no LLM | Raised before they ask |
| 11:15 to 12:45 | Soham | Slides 11 and 12 | Back to her; two stores; the ask |
| 12:45 to 15:00 | All | | Q&A |

**If running long:** cut Loyalty to one sentence. Never cut the two customers, the Model page or the "no LLM" moment.

---

## Before you start (10 minutes before)

1. Terminal: `uvicorn api.main:app --reload`. Open http://127.0.0.1:8000.
2. Light theme. Browser zoom 110% or 125%.
3. Open **Overview**, **C10001** and **C10000** once each so they are cached. **Leave the browser on C10000**, scrolled to the top: it is the first screen after the film. Leave the Overview sliders at Protect 20%, Win back 12%.
4. Film: `C10000_story.mp4` full screen on top of the browser, paused on the first frame. Test the sound on the room speakers. Keep `C10000_story_silent.mp4` ready.
5. Deck open in a second window on slide 1. Notifications off. Deck PDF on the desktop.
6. Leaflets face down with Nilanjana and Rima.

---

# Act 1: One person

## 0:00 to 0:20, Soham: before the film

Lights down if you can. Stand away from the laptop. Slow.

> "Before we show you a single number, we'd like you to meet one of your customers.
> She's loyal. For three years she's shopped with you every few weeks.
> Over the next few months, she'll quietly stop coming in. No complaint, no goodbye, and nothing in your sales reports will flag it.
> *(pause)* Watch."

Press play. Step back.

## 0:20 to 1:05, the film

Nobody speaks. Let the end card hold until it fades. If the audio fails, let it run; the captions carry it.

## 1:05 to 1:25, Soham: the bridge

Close the film. The app is already showing C10000.

> "C10000 isn't real; all our data is synthetic, and it says so on every screen. But every one of you has thousands of her.
> And this year, while everyone pitches you a chatbot, we built something you can audit, number by number.
> **Viditi, show them where she lives.**"

---

# Act 2: Two people, then everyone (Viditi)

## 1:25 to 3:00, C10000: the film, as a real screen

> "What you just watched is this screen. Same customer, same numbers.
> C10000: 38, Manchester, a loyal family shopper. About fifty visits, about £1,900 over three years."

Point to the summary.
> "The model gives her only a [27%] chance of still being an active customer. If she stays, she's worth about [£345] next year. Today we expect only [£92]. So [£253] is at risk."

Point to **Why this customer was flagged**.
> "And it tells us why, in a sentence anyone can act on: last visit 102 days ago, five times her usual gap of 20 days."

Point to **Days between visits**.
> "Twenty days, then 26, 31, 38, 60. Orange means much longer than her usual. Exactly what you saw in the film."

Point to **Recommended next step**.
> "So we invest: early access plus an offer in Womenswear, her favourite category, by app and email."

## 3:00 to 4:00, C10001: same warning sign

**Click:** the **C10001, low value** chip.

> "Now C10001. 24, Leeds. Small baskets, about six pounds a visit, every six weeks or so last year. Then nothing since Black Friday.
> Same warning sign. In fact the model is even more sure she's gone: [92%]. Last visit 306 days ago, seven times her usual gap, and she's stopped opening our emails.
> But if she stayed, she'd be worth about [£33] a year."

## 4:00 to 4:40, the comparison

Scroll to **Same warning sign, different decision**.

> "Side by side. Same model, same signal, two completely different decisions.
> For C10000 we spend about [£8] of personal attention to get back about [£50].
> For C10001 we spend about [£1]: one automated email, no personal offer, for about [£4] back.
> *(pause)* Not every customer deserves the same pound. This tells you where to spend, and just as importantly, where not to."

## 4:40 to 6:40, Overview: now do it for everyone

> "That's two customers. Now imagine doing this every morning, for every customer you can identify."

**Click:** Overview. Let the number settle.

> "Across our customers, about [£540k] of next year's revenue sits with people like C10000 and C10001, people who may already be drifting away.
> How much can we realistically win back? About [£83.9k]. Notice the label: *assumption*."

**Click:** drag **Protect** from 20% to 30%, then back.

> "These two sliders are the only guesses on this page: what share of drifting customers a campaign keeps. We set them low on purpose, 20% and 12%. Campaign cost is about [£20k] and the net return about [£64k]: roughly three pounds back for every pound spent. Even if we're wrong by half, it still pays. A pilot replaces both numbers with measured ones."

**Click:** the **Customers** switch on the bar, then back to **Revenue at risk**.

> "By number of customers, the orange group is small. By money, it carries far more than its share. That's C10000's group."

**Click:** the **Protect** tile.

## 6:40 to 7:30, Segments: the two customers, at scale

> "Every customer gets the same two questions: how much are they worth if we keep them, and how likely are they to have drifted?"

Point to each tile, one line each:
- **Protect:** "C10000 lives here. High value, slipping. Personal attention, quickly."
- **Grow:** "High value and happy. Reward them; no discounts they'd have shopped without."
- **Win back:** "C10001 lives here. Lower value, probably gone. Cheap and automated."
- **Maintain:** "Lower value and steady. Leave them alone and save the money."

## 7:30 to 8:15, Loyalty: one lever

**Click:** Loyalty.

> "One more lever. Customers registered as members visit about 18% more often and leave less. Primark doesn't run a classic loyalty card, so read this as: what would a members programme on the app be worth? It's association, not proof, so this slider lets you decide how much you believe. And who you invite matters more than how many."

**Click:** drag **share of the gap the programme really causes** to 25%, then back to 50%.

**Handover:** **"You've seen what it says. Dibyendu built the models, and he's the reason we hold ourselves to such a strict test."**

---

# Act 3: Can you trust it?

## 8:15 to 10:15, Dibyendu: the proof (Model page)

**Click:** Model.

> "When we designed the models, I set one rule: nothing goes on screen unless it beats a simple method on data it has never seen. So we trained on older data and tested on a full year we held back."

Point to the strip:
- "Average miss per customer, about [£38]. The standard RFM method most retailers use misses by about [£42]. About 10% better, on a fair test."
- "Across all customers, the total forecast lands within about 1% of what really happened."
- "Spotting who has left scores [0.85], where 0.5 is a coin flip."

Scroll to the **scorecard ladder**.
> "Each row adds one idea. For spend, gradient boosting does most of the work. The visit model adds what boosting can't: the probability a customer has already gone. That's what put C10000 in Protect and C10001 in Win back. I chose the blend because it gets the total right, and the total is what a budget is set on."

Point to **Did the visit model learn the truth?**
> "And a check you rarely get: because the data is synthetic, we know the hidden settings that produced it. The model was never shown them and recovers them closely."

**Handover:** **"And for the question you're probably about to ask, Viditi."**

## 10:15 to 11:15, Viditi: why there is no LLM (slide 10)

> "You may be wondering where the generative AI is. There's no LLM in the engine, and that's deliberate.
> One: the question is about numbers. Forecasting spend and churn from transactions is what statistics and machine learning do best.
> Two: same input, same answer. Every number can be repeated, traced and tested on a year it never saw.
> Three: customer data stays inside Primark. Nothing goes to an outside AI service. It even runs offline, on this laptop.
> Four: it scores millions of customers in minutes, with no per-call bill.
> Language AI belongs on top: a short briefing for the CRM team, a first draft of the message, with a person approving every one. Maths for the numbers, rules you can read for the decisions, language only for the words. **Dibyendu?**"

**Dibyendu:** "Same input, same answer, every time. That's what makes it auditable."

**Handover:** **Viditi: "Soham, back to her."**

## 11:15 to 12:45, Soham: the close (slides 11 and 12)

> "Back to C10000. Today, nobody would notice she's gone. With this, the CRM team sees her in the morning, with a reason and a next step. And it doesn't waste a pound on customers who won't repay it.
>
> Primark is opening stores in the United States. Every new store there, and every store in Manchester, faces the same question: of everyone walking in today, who will still be coming back in a year? No sales report answers it. This does.
>
> To make it real, we'd ask for three things: a sample of real identified-customer data, one campaign test with a control group to replace our two assumed save rates, and a decision on where to start. We'd start with Protect.
>
> Thank you."

**Nilanjana and Rima** hand out leaflets, front side up, from both ends of the table.

**Soham:** "We're happy to take questions. Each of us will answer on the part we built."

Rules: never claim the US stores have a problem. Do not promise a store-by-store view.

---

## Likely questions and answers

Answer in one or two sentences, then stop.

**How are these numbers actually made?**
Use `NUMBERS_SCRIPT.md` (the 60-second version).

**Why no LLM? Isn't that behind the times?**
It's a choice. Numbers need models you can test and audit; an LLM can't be backtested the same way, varies run to run, and would send customer data outside. Language AI belongs on top, for briefings and drafts, with human approval.

**Will you add an LLM later?**
Yes, for words only: a briefing per customer and a draft message in Primark's voice. It never calculates, and a person approves every message.

**Couldn't an LLM predict churn too?**
It could guess, but not in a way you can test against a held-out year, reproduce exactly or explain. For tabular forecasting, gradient boosting and survival-style models are the established, auditable tools.

**Is this real data?**
No, synthetic, labelled on every screen. 20,000 customers built to behave like UK and Ireland shoppers. Real data would fill the same five tables after a cleaning step.

**Are C10000 and C10001 real?**
Both are hand-written examples inside the synthetic data, chosen to show the two ends of the decision. C10001 is scored but kept out of training, so she doesn't influence anyone else's numbers.

**How are customers put into groups?**
Two rules: top 30% by value is "high value"; a 50% or higher chance of having drifted is "high risk". Primark can move both.

**Why these actions?**
Sensible starting rules, not learned from results. A campaign test with a control group tells us which actions really work.

**Where does the £83.9k come from?**
Assumed save rates and costs, shown on Segments and adjustable on Overview. Contact costs are low, so each campaign pays even at very low save rates; at half our rates it still pays. A campaign test measures the real numbers.

**Did C10000 really come back, in the film?**
No. The film shows what the system is built to make happen. Her 73% and £253 are real model outputs on synthetic data; whether a message brings her back is what a pilot measures.

**Are you saying our US stores are underperforming?**
No. We have no data on them and make no claim. Every new store faces the same question in its first months.

**Could this work for a new US store?**
For shoppers identified through the app or CRM, yes in principle. The model allows someone to visit once and never return, the typical new-store pattern. It needs a few months of history and is untested on US data.

**Why not just use gradient boosting?**
For spend accuracy, boosting alone is nearly as good, and we show that. The visit model gives the chance a customer has left, which boosting can't.

**Why a blend?**
Per customer, stacked is slightly closer. For budgeting the total matters, and the blend gets it within about 1%.

**How sure are you about one customer?**
The demo shows a point estimate, not a range. Uncertainty ranges are a planned addition.

**Are gender and age used?**
Yes, currently as inputs to spend. We'd remove or review them, and check fairness, before real use.

**How does it fit our systems?**
It's a scoring layer. Scores run in a batch on Primark's data platform and feed the CRM and marketing tools you already use.

**How is this different from Salesforce, Optimove or Adobe?**
Those platforms run campaigns; we don't. This is a scoring layer Primark owns: value and risk in pounds per customer, tested openly against simple methods, every assumption visible. It would feed those tools, not replace them.

**Does a members programme really cause higher spend?**
We can't tell from this data. That's why the slider lets you choose.

**How often would it update?**
The pipeline runs in about a minute on a laptop. Weekly is realistic.

**What would it cost for real?**
Not answered by this demo. We'd come back with a scoped estimate.

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Film has no sound | Let it play; the captions carry it. Do not restart it |
| Page shows "Something went wrong" | Soham restarts `uvicorn api.main:app --reload` and refreshes. Viditi says "ten seconds" and keeps talking |
| Laptop fails entirely | Switch to the deck PDF: slide 3 carries the two customers, slide 9 the evidence, slide 10 the "no LLM" case |
| Number on screen differs from this script | Use the screen. Say nothing about it |
| A presenter freezes | The next person says their handover line and carries on. Nobody comments on it |
| Projector washes out light theme | Click the theme switch for dark |
