# Midterm market script and Q&A

Oct 28, 2026 · Aaron. Copy of the shared doc "Midterm market script and Q&A". If they differ, the shared doc
is the one being edited live; numbers come from `reports/tables/key_numbers.json`.

The market part runs about 6 minutes over 7 slides. The finding: Polymarket prices are well calibrated in all four
categories, and no model we built beats them out of sample. Figures are in `reports/figures/`; the full
reasoning is in `reports/midterm/market_writeup.md`.

## Slide by slide

Seven slides, about 6 minutes at a calm pace (about 130 words a minute). Say the bold line on each slide first;
everything after it is support. If you run long, cut slide 5 to its bold line.

| Slide | Topic | Figure | Time |
| --- | --- | --- | --- |
| 1 (deck 4) | A price is a probability | none | 0:45 |
| 2 (deck 5) | Data and how we built the sample | none | 0:50 |
| 3 (deck 6) | The crowd is well calibrated | fig1, fig2 | 0:50 |
| 4 (deck 7) | Is there a favorite-longshot bias? | fig4 | 1:00 |
| 5 (deck 8) | Accuracy over time and by category | fig3 | 0:40 |
| 6 (deck 9) | Can a model beat the price? | fig5 | 1:10 |
| 7 (deck 10) | Takeaways, limits, and the final | none | 0:50 |

### Slide 1. A price is a probability (0:45)

On screen: "Can AI beat the crowd?" and three numbers: 7,479 resolved markets, 4 categories, Jun to Oct 2026.

Say: **Thank you, Leo. As Leo mentioned, our question is whether prediction-market prices are good probabilities.** On Polymarket, a Yes share pays one dollar if the event happens. Suppose a share costs 40 cents, but you believe the chance is 60 percent. Then buying it is profitable on average. This is the formula on the slide: expected profit equals p, your belief, minus c, the price. Traders keep buying or selling until the price matches the crowd's belief. So the price can be read as a probability, and we can test it. We ask two questions. First, is the price calibrated? Second, can a model do better?

### Slide 2. Data and how we built the sample (0:50)

On screen: a three-step flow. Resolved markets (catalog + resolutions) → price before close (4.1M trades) →
grade against the outcome.

Say: **Here is our data.** We used all Yes/No markets in our four categories that closed between June and October 2026. This gives 7,479 markets. For each market, we recorded the price at four points before it closed: seven days, three days, one day, and six hours. The price is the last trade before each point, from 4.1 million trades. We also checked the order book. It covers only 22 percent of these markets, but where both exist, the two prices agree closely, with a correlation of 0.92.

### Slide 3. The crowd is well calibrated (0:50)

On screen: fig1 (calibration curve, 24h), then fig2 (one panel per category) as a build.

Say: **This figure shows our main result.** We group markets by their price one day before close. Then we check how often each group actually happened. If prices are calibrated, the points lie on the diagonal, and they do. When the market says 30 percent, the event happens about 30 percent of the time. The same holds in all four categories, shown on the right. The shaded band is a 95 percent interval. We resample whole events, not single markets, because markets in one event are linked. For example, only one film can win Best Picture.

### Slide 4. Is there a favorite-longshot bias? (1:00)

On screen: fig4 (calibration slope by month), plus two numbers: slope 1.08 with all prices, 1.00 for prices
between 2 and 98 cents.

Say: **Next, we test the favorite-longshot bias that Leo introduced.** We summarize calibration with one number: the slope from a logistic regression of the outcome on the price. A slope of one is perfect. A slope above one means long shots are overpriced. Six hours before close, the slope is 1.08, which is a small sign of the bias. However, it comes only from extreme prices, below 2 cents or above 98 cents. Without them, the slope is 1.00. The slope also changes from month to month, between 0.93 and 1.09, and every monthly interval includes one. So the bias is small and not stable.

### Slide 5. Accuracy over time and by category (0:40)

On screen: fig3 (Brier score by horizon, one line per category).

Say: **This figure shows accuracy over time.** We use the Brier score, the average squared error of the price, so lower is better. Accuracy improves as the event gets closer. The score falls from 0.074 one week before close to 0.038 six hours before. Politics improves the most, and Economy remains the hardest category near the close.

### Slide 6. Can a model beat the price? (1:10)

On screen: fig5 (each model's Brier minus the market's, with 95% intervals) and one line: "above zero = worse
than the market".

Say: **Next, we ask whether a model can beat the price.** We trained two models. The first is logistic regression, which adjusts the price to correct small biases by category and by time. The second is gradient boosting, which combines many small decision trees, where each tree corrects the errors of the previous ones. It uses the price plus 18 other features, such as recent price changes, trading volume, and time to the deadline. We trained on markets that closed before September and tested on September and October. Neither model beats the market price. Most of the boosting model's weight is on the price itself. This matches the previous result: a bias that changes every month cannot be learned.

### Slide 7. Takeaways, limits, and the final (0:50)

On screen: three takeaways, two limits, and one line for the final: "An informed trader is one who beats the
price, not one who wins a lot."

Say: **To summarize, the market is hard to beat.** Prices are well calibrated in all four categories. The favorite-longshot bias is small and unstable. And our models do not beat the price. We have two limitations. Some markets close early when the event happens, and we have only one test period. For the final project, this gives us a clear definition. An informed trader is not someone who wins often, because buying at 95 cents wins about 95 percent of the time. An informed trader consistently beats the price they paid. Next, Jiahong will show which wallets pay low prices.

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
