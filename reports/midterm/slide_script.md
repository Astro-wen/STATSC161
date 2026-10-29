# Midterm market script and Q&A

Oct 28, 2026 · Aaron. Copy of the shared doc "Midterm market script and Q&A". If they differ, the shared doc
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
| 6 | Can a model beat the price? | fig5 | 1:30 |
| 7 | Takeaways, limits, and the final | none | 1:00 |

### Slide 1. A price is a probability (0:45)

On screen: "Can AI beat the crowd?" and three numbers: 7,479 resolved markets, 4 categories, Jun to Oct 2026.

Say: **Thanks, Leo. So like Leo said, our big question is: when Polymarket says something has a 30 percent chance, should we actually believe it?** Here's the quick intuition. Take a market like "Will the Lakers win tonight?" A Yes share pays one dollar if they win and zero if they lose. Say it's trading at 40 cents. If you think the Lakers really have a 60 percent chance, that's a good deal: on average you pay 40 and get 60 back. That's this formula. Expected profit is p, what you believe, minus c, the price. So people keep buying until the price matches what the crowd thinks, and that's why we can treat the price as a probability and grade it. Leo also mentioned a classic finding from horse racing: long shots tend to be overpriced. So we asked two things. Is the price right? And can a model do better?

### Slide 2. Data and how we built the sample (1:00)

On screen: a three-step flow. Resolved markets (catalog + resolutions) → price before close (4.1M trades) →
grade against the outcome.

Say: **Here's what we worked with.** We took every Yes/No market in our four categories, politics, tech, entertainment and economy, that closed between June and October. Think questions like "Will the Fed cut rates in September?" That's 7,479 markets. For each one we went back in time and asked: what was the price a week before it closed? Three days before? One day? Six hours? To get that, we used the last trade before each of those points, out of about 4.1 million trades. Quick note on why trades: we first tried the order book, but it only covered about a fifth of these markets. Where we had both, they basically agreed, a correlation of 0.92 and less than a cent apart. So trades it is.

### Slide 3. The crowd is well calibrated (1:00)

On screen: fig1 (calibration curve, 24h), then fig2 (one panel per category) as a build.

Say: **So, is the crowd right? This is the main picture.** We group markets by their price a day before close, and check how often they actually happened. If the market is honest, everything sits on this diagonal. And it does: when the market says 30 percent, it happens about 30 percent of the time. On the right, it's the same story in all four categories. One detail on the shaded band. It's our 95 percent interval, and we built it by resampling whole events, not single markets. Why? Think of the Oscars. Best Picture has ten markets, one per film, but only one film can win. Those aren't ten independent coin flips, so we treat the whole event as one unit.

### Slide 4. Is there a favorite-longshot bias? (1:15)

On screen: fig4 (calibration slope by month), plus two numbers: slope 1.08 with all prices, 1.00 for prices
between 2 and 98 cents.

Say: **Now, what about that horse-racing bias we introduced earlier?** To check it, we squeeze calibration into one number, the slope. Technically it's the slope from a logistic regression of what happened on the price, but the idea is simple. One means perfect. Above one means the market is too timid: long shots are a little too expensive and favorites a little too cheap. Six hours before close we get 1.08, so there is a small trace of the bias. But here's the catch. It comes entirely from the extreme contracts, the ones under 2 cents or over 98 cents. Think of bets like a long-shot candidate winning an election. Take those out, and the slope is exactly 1.00. And month by month, like in this chart, it bounces between 0.93 and 1.09, and every interval includes 1. So the bias is small, and it doesn't stay put.

### Slide 5. Accuracy over time and by category (0:45)

On screen: fig3 (Brier score by horizon, one line per category).

Say: **Next, timing.** This is the Brier score, which is basically how far off the price was from what actually happened. Lower is better. And it makes sense: the closer you get to the event, the better the price. A week out it's 0.074, six hours out it's 0.038, roughly half. Think of an election: a week before, there's still a lot that can happen; the night before, most of the information is already out. Politics improves the most, and economy stays the hardest to call.

### Slide 6. Can a model beat the price? (1:30)

On screen: fig5 (each model's Brier minus the market's, with 95% intervals) and one line: "above zero = worse
than the market".

Say: **So the price is pretty good. Can AI beat it?** We tried two models. The first is logistic regression, the standard tool for predicting a yes-or-no outcome: it turns inputs into a probability between 0 and 1. We give it the market price, so it learns small corrections, like "when the market says 10 percent, it's really 8," and it can correct differently by category and by how far we are from the close. The second is gradient boosting. It builds a few hundred small decision trees one after another, and each new tree focuses on the mistakes the earlier ones made. Think of a team of analysts where each one fixes what the last one got wrong. That lets it pick up patterns a straight line would miss. We gave it the price plus 18 other things you'd know at that moment, like how the price moved over the last day, trading volume, how many people are trading, and how long until the deadline. To keep it fair, we trained on everything that finished before September and tested on September and October, so the model never sees the future. And the answer: neither one beats the raw price. The simple correction actually does slightly worse. When we look inside the boosting model, it leans almost entirely on the price itself. That ties back to the bias slide: if the bias keeps changing month to month, you can't learn it in the summer and use it in the fall.

### Slide 7. Takeaways, limits, and the final (1:00)

On screen: three takeaways, two limits, and one line for the final: "An informed trader is one who beats the
price, not one who wins a lot."

Say: **So, three takeaways.** One, prices are well calibrated across all four categories. Two, the favorite-longshot bias is small and unstable. Three, no model we built beats the price. Two honest limits. Some markets close early, like "Will X happen by December?" resolving the day it happens, so "a day before close" means slightly different things for different markets. And we only have one test period. But here's why this matters for our final. If the market is this good, winning a lot doesn't mean much. If you only buy things priced at 95 cents, you'll win about 95 percent of the time, and that's not skill. A truly informed trader is someone who keeps beating the price they paid. So the next question is: who's paying the low prices, who's buying the long shots? Jiahong, take it away.

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
