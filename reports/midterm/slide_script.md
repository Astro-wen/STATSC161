# Midterm market script and Q&A

Oct 27, 2026 · Aaron. Copy of the shared doc "Midterm market script and Q&A". If they differ, the shared doc
is the one being edited live; numbers come from `reports/tables/key_numbers.json`.

The market part runs 7 minutes over 7 slides. The finding: Polymarket prices are well calibrated in all four
categories, and no model we built beats them out of sample. Figures are in `reports/figures/`; the full
reasoning is in `reports/midterm/market_writeup.md`.

## Slide by slide

Seven slides, 7 minutes at a calm pace (about 130 words a minute). Say the bold line on each slide first;
everything after it is support. If you run long, cut slide 5 to its bold line.

| Slide | Topic | Figure | Time |
| --- | --- | --- | --- |
| 1 | A price is a probability | none | 0:45 |
| 2 | Data and how we built the sample | none, a 3-step flow | 1:00 |
| 3 | The crowd is well calibrated | fig1, fig2 | 1:00 |
| 4 | Is there a favorite-longshot bias? | fig4 | 1:15 |
| 5 | Accuracy over time and by category | fig3 | 0:45 |
| 6 | Can a model beat the price? | fig5 | 1:15 |
| 7 | Takeaways, limits, and the final | none | 1:00 |

### Slide 1. A price is a probability (0:45)

On screen: "Can AI beat the crowd?" and three numbers: 7,479 resolved markets, 4 categories, Jun to Oct 2026.

Say: **"Our question is simple: is the market's price a good probability, and can a model do better?"** On
Polymarket a Yes share pays one dollar if the event happens. If you think the chance is p and the share costs
c, your expected profit is p minus c. So people buy until the price matches what the crowd believes, which
makes the price a forecast we can grade. A classic finding from betting markets is the favorite-longshot
bias: long shots are overpriced. We test whether that shows up here.

### Slide 2. Data and how we built the sample (1:00)

On screen: a three-step flow. Resolved markets (catalog + resolutions) → price before close (4.1M trades) →
grade against the outcome.

Say: **"We took every Yes/No market in our four categories that resolved from June to October, and read its
price at four points before it closed."** The course database has no category field, so we used
Polymarket's own event tags: politics, tech, pop culture, economy. That gives 7,479 markets. For each one we
read the price 6 hours, 24 hours, 3 days and 7 days before close. We first tried the hourly order book, but it
only recorded about a fifth of these markets. So we used the last trade before each point, from 4.1 million
trades. Where both sources exist they agree closely: correlation 0.92, median gap under one cent.

### Slide 3. The crowd is well calibrated (1:00)

On screen: fig1 (calibration curve, 24h), then fig2 (one panel per category) as a build.

Say: **"When the market says 30 percent, it happens about 30 percent of the time."** Each dot groups markets
by their price a day before close and shows the share that actually resolved Yes. Perfect calibration is the
diagonal, and the dots sit on it. The shaded band is a 95 percent interval. We resample whole events to build
it, because markets in one event are linked: only one film can win Best Picture. Treating them as independent
would make the band far too narrow. The same picture holds in all four categories.

### Slide 4. Is there a favorite-longshot bias? (1:15)

On screen: fig4 (calibration slope by month), plus two numbers: slope 1.08 with all prices, 1.00 for prices
between 2 and 98 cents.

Say: **"We find a faint trace of the bias, but it is not stable enough to matter."** We summarize calibration
with one number: regress the outcome on the log-odds of the price. A slope of 1 is perfect; above 1 means
prices are too timid, so long shots are overpriced. Six hours before close the slope is 1.08, and its interval
just excludes 1. But it comes entirely from prices under 2 cents or over 98 cents: drop those and the slope is
1.00. And month by month it moves between 0.93 and 1.09, with every interval crossing 1. So it is a weak effect
that changes direction.

### Slide 5. Accuracy over time and by category (0:45)

On screen: fig3 (Brier score by horizon, one line per category).

Say: **"Prices get sharper as the event gets closer, and economic questions stay the hardest."** The Brier
score is the average squared gap between the price and what happened, so lower is better. Across all markets
it roughly halves from a week out to six hours out, from 0.074 to 0.038. Politics improves the most. From three
days out to the close, Economy is the hardest category to call.

### Slide 6. Can a model beat the price? (1:15)

On screen: fig5 (each model's Brier minus the market's, with 95% intervals) and one line: "above zero = worse
than the market".

Say: **"We tried to beat the crowd with two models, and neither did."** We trained on events that finished
before September and tested on September and October. No event sits on both sides, and every feature uses only
trades before the time point, so nothing leaks. Model one re-calibrates the price, letting the correction
differ by category and horizon. Model two is gradient boosting with the price plus 18 features known at the
time: recent price moves, order flow, volume, number of traders, market age, time to the deadline, category.
Both come out no better than the raw price, and the re-calibration is slightly worse. When we shuffle each
feature to see what the model relies on, almost all the weight is on the price itself. That fits slide 4: a
bias that changes direction cannot be learned in summer and used in autumn.

### Slide 7. Takeaways, limits, and the final (1:00)

On screen: three takeaways, two limits, and one line for the final: "An informed trader is one who beats the
price, not one who wins a lot."

Say: **"The market as a whole is hard to beat, and that gives us a clean definition for the final."** Three
takeaways: prices are well calibrated in all four categories; the favorite-longshot bias is faint and
unstable; and no model we built beats the price. Two limits: some markets close early because the event
happened, so "24 hours before close" means slightly different things for Yes and No markets; and we have one
test period. For the final: an insider is not someone who wins a lot, since buying at 95 cents wins a lot too.
It is someone whose bets keep beating the price they paid. Jiahong will now show who buys the long shots.

## Backup slides

Keep these after the last slide and open one only if a question calls for it.

- **B1. Train and test.** Train: 841 events, 3,215 markets, all closed before Sep 1. Test: 860 events, 3,511
  markets. An event that straddles Sep 1 goes wholly to test.
- **B2. Mid-range prices only.** Restricting the test set to prices between 5 and 95 cents, the 24-hour Brier
  is 0.148 for the market and 0.150 for both models. The near-certain markets are not what makes the market
  look good.
- **B3. Slopes by category.** At 24 hours: Politics 1.03, Technology 1.11, Entertainment 1.12, Economy 0.92.
  Only Entertainment's interval sits just above 1 (1.00 to 1.29); the other three include 1. With four
  categories tested, one borderline result is not unusual by chance.

## Q&A prep

Short answers first; add the second sentence only if they push.

1. **"Isn't the favorite-longshot bias well known? Why don't you see it?"** We do see a trace of it near the
   close: the slope is 1.08 six hours out. But it comes only from prices under 2 cents or over 98 cents, and
   it flips direction from month to month (slide 4). In our data it is much weaker than what the racetrack
   studies report.
2. **"Why use trade prices instead of the order book?"** The hourly book only recorded about 22% of these
   markets. Where both exist, the last trade and the book midpoint agree closely: correlation 0.92, median gap
   under a cent (slide 2).
3. **"How did you avoid data leakage?"** Every feature uses only trades before the time point. Training uses
   events finished before September 1, testing uses the rest, and no event is on both sides. We left out the
   catalog's volume fields because they are totals recorded after the fact.
4. **"Why resample by event for the confidence intervals?"** Markets in one event are dependent: in a Best
   Picture event, exactly one of ten markets resolves Yes. Treating them as independent would make the
   intervals far too narrow.
5. **"Why Brier score and not accuracy?"** We are judging probabilities, not yes/no calls. Brier and log loss
   are proper scoring rules: a forecaster scores best only by reporting what they actually believe. Accuracy
   would call 51% and 99% the same prediction.
6. **"Most markets sit near zero. Doesn't that inflate how good the market looks?"** Yes, many multi-outcome
   events have long-shot markets priced under 2 cents. That is why we also report results on prices between 5
   and 95 cents (backup B2): neither model beats it there either, with a Brier of 0.148 at 24 hours against
   0.150 for both models.
7. **"How did you define the four categories?"** With Polymarket's own event tags: politics, tech, pop-culture
   for Entertainment, and economy. When an event carries two of them, it goes to the rarer one.
8. **"What about markets that close early because the event happened?"** That is a real limitation. For a "by
   date" market that resolves Yes early, 24 hours before close is just before the news, while a No market
   closes on its deadline. We plan to split those two groups next.
9. **"Is one test period enough?"** It is one period, September to October, so we would not claim the result
   holds forever. The monthly slopes (slide 4) suggest the market's small errors do not persist long enough to
   exploit.
10. **"So is there nothing to find for the final?"** The opposite: because the price is so good, beating it is
    a strong signal. The final looks for traders who keep beating the price they paid.

## Numbers to remember

| What | Number |
| --- | --- |
| Resolved Yes/No markets in the 4 categories, Jun 1 to Oct 25 | 7,479 |
| With a price 24h before close | 5,805 markets, 1,610 events |
| Trades used to read prices | 4.1 million |
| Brier score, all markets, 7d / 3d / 24h / 6h before close | 0.074 / 0.057 / 0.049 / 0.038 |
| Brier at 24h: Technology / Politics / Entertainment / Economy | 0.038 / 0.043 / 0.054 / 0.068 |
| Calibration slope at 6h, all prices | 1.08 (95% CI 1.01 to 1.16) |
| Calibration slope at 6h, prices 2c to 98c | 1.00 (0.89 to 1.11) |
| Monthly slope at 24h, range | 0.93 to 1.09 |
| Test set | 860 events, 3,511 markets, Sep to Oct |
| Test Brier at 24h: market / re-calibration / boosting | 0.0513 / 0.0518 / 0.0518 |
| Test AUC at 24h, market price | 0.971 |
| Order book coverage of these markets | about 22% |
| Trade price vs book midpoint | correlation 0.92, median gap 0.9c |
