/** Author the four editable content slides from the recorded study results. */
export function buildWalletSlides(presentation, payload) {
  const { summary: S, histogram } = payload;
  const M = Object.fromEntries(S.metrics.map(r => [r.model, r]));
  const ink = '#263449', blue = '#315C8C', orange = '#DF7137', muted = '#627085';
  presentation.theme.defaultFont = 'Arial';
  function text(slide, name, value, x, y, width, height, size = 24, bold = false, color = ink) {
    const shape = slide.shapes.add({geometry: 'textbox', name, position: {left:x, top:y, width, height}, fill:'none', line:{fill:'none', width:0}});
    shape.text = value;
    shape.text.style = {typeface:'Arial', fontSize:size, bold, color, insets:0, verticalAlignment:'top', alignment:'left', autoFit:'none', wrap:'square'};
    return shape;
  }
  function slide(title) {
    const s = presentation.slides.add({width:1280,height:720});
    s.background.fill='#FFFFFF';
    text(s,'slide-title',title,64,42,1152,62,44,true);
    return s;
  }
  const axis = {textStyle:{fontSize:20,fill:muted},line:{style:'solid',fill:'#CBD0D8',width:1}};

  const s1=slide('Question and data');
  text(s1,'research-question','How well do wallet characteristics predict average purchase price, and does boosting improve on linear regression?',64,144,510,181,31,true);
  text(s1,'sample-size','55,952 wallets',64,354,500,48,34,true,blue);
  text(s1,'data-description','One row per wallet\nTarget: volume weighted price per share\nAll wallets retained. Confirmed flag excluded.',64,423,525,140,25);
  text(s1,'cohort-scope','Selected event cohort. Prices summarize observed trading history.',64,635,1140,32,20,false,muted);
  const fractions=[];
  for(let i=0;i<5;i++) fractions.push(Number(histogram.slice(i*5,(i+1)*5).reduce((sum,r)=>sum+r.fraction,0).toFixed(10)));
  s1.charts.add('bar',{
    position:{left:636,top:143,width:580,height:415},
    title:'Training price distribution',titleTextStyle:{fontSize:26,bold:true,fill:ink},
    categories:['0.0–0.2','0.2–0.4','0.4–0.6','0.6–0.8','0.8–1.0'],
    series:[{name:'Share of training wallets',values:fractions,fill:blue}],
    barOptions:{direction:'column',gapWidth:18},hasLegend:false,
    xAxis:{...axis,title:'Average purchase price ($)'},
    yAxis:{...axis,min:0,max:.5,majorUnit:.1,numberFormatCode:'0%',majorGridlines:{fill:'#E8ECF1',width:1}},
    dataLabels:{showValue:false},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'
  });
  s1.speakerNotes.text='Our question is how well wallet trading characteristics predict average purchase price, and whether gradient boosting improves on linear regression. The dataset contains 55,952 wallets, with one row per wallet. The target is the volume weighted price of shares each wallet bought. The histogram summarizes training wallets and uses five broader price bins for readability. We retain all wallets and completely exclude the confirmed flag. This cohort comes from five selected event groups, so we describe the wallets in this dataset. A higher or lower purchase price does not itself tell us whether the wallet made a profit.\n\nSources: wallet_analysis/data/wallet_features.csv; the opening data dictionary in the course insider_demo.ipynb; tables/target_histogram_training.csv. The native slide histogram aggregates each five adjacent bins from Figure 01. No target values from the final test set enter this chart.';

  const s2=slide('Approach');
  text(s2,'split-heading','One fixed wallet split',64,143,530,40,28,true);
  text(s2,'split-counts','44,761 training wallets\n11,191 test wallets',64,201,520,93,31,false,blue);
  text(s2,'validation-heading','Model selection within training',64,330,535,38,27,true);
  text(s2,'validation-text','Five-fold validation selects one of six boosting configurations.',64,380,520,82,25);
  text(s2,'transformation-text','Log-transform five skewed predictors.\nStandardize inputs for linear regression.',64,493,535,82,24);
  const t=s2.tables.add({rows:4,columns:2,left:653,top:151,width:563,height:327,columnWidths:[223,340],values:[['Comparison','Prediction rule'],['Mean baseline','Training mean for every wallet'],['Linear regression','Additive associations'],['Gradient boosting','Nonlinear patterns and interactions']]});
  t.rows[0].height=51;
  for(let i=1;i<4;i++)t.rows[i].height=92;
  t.borders.assign({style:'solid',fill:'#D9DFE7',width:.7});
  for(let i=0;i<4;i++)for(let j=0;j<2;j++){
    const cell=t.getCell(i,j);
    cell.fill=i===0?'#263F5C':'#FFFFFF';
    cell.text.style={fontSize:23,typeface:'Arial',color:i===0?'#FFFFFF':ink,bold:i===0,verticalAlignment:'middle',insets:{left:13,right:12,top:9,bottom:9}};
  }
  text(s2,'predictor-list','Inputs: trade count, markets traded, observed span, concentration, spending, largest purchase.',653,505,563,110,23);
  text(s2,'evaluation-rule','Same test wallets for every model. Primary metric: MAE. Secondary checks: RMSE and R².',64,641,1152,35,20,false,muted);
  s2.speakerNotes.text='We reserve twenty percent of the wallets for final evaluation, using one fixed random split. This gives 44,761 training wallets and 11,191 test wallets. Every method receives exactly the same test wallets. Five-fold validation happens entirely inside training. We compare a mean baseline, an additive linear regression, and histogram gradient boosting, which can capture nonlinear patterns and interactions. The inputs are trade count, market count, observed activity span, concentration, total spending, and largest purchase. Five skewed predictors use log of one plus the value. Linear regression also standardizes its inputs using training statistics. We select boosting settings from a small six-configuration grid using validation MAE. The test set stays outside model selection.\n\nSources: code/analyze_wallet_prices.py; tables/wallet_split.csv; tables/cv_grid_full.csv; https://scikit-learn.org/1.7/modules/cross_validation.html; https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html. Fixed settings: 250 iterations, learning rate 0.06, minimum leaf size 30, early stopping disabled. Grid: maximum leaves 7, 15, 31 and L2 regularization 0 or 1. Both learned models fit squared error. Selected full specification: 31 leaves and L2=1.';

  const s3=slide('Results');
  const names=['Mean baseline','Linear regression','Gradient boosting'];
  s3.charts.add('bar',{
    position:{left:64,top:137,width:774,height:395},
    title:'Test MAE in cents per share',titleTextStyle:{fontSize:26,bold:true,fill:ink},
    categories:names,
    series:[{name:'MAE',values:names.map(n=>Number((M[n].MAE*100).toFixed(8))),fill:blue,points:[{idx:0,fill:'#9AA4B2'},{idx:1,fill:blue},{idx:2,fill:orange}]}],
    barOptions:{direction:'column',gapWidth:100},hasLegend:false,
    xAxis:{...axis,textStyle:{fontSize:21,fill:ink}},
    yAxis:{...axis,min:0,max:27,majorUnit:5,numberFormatCode:'0',majorGridlines:{fill:'#E8ECF1',width:1}},
    dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00',textStyle:{fontSize:25,bold:true,fill:ink}},
    chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'
  });
  text(s3,'relative-improvement','15.4%',885,157,330,92,74,true,orange);
  text(s3,'relative-improvement-label','lower MAE than\nlinear regression',885,266,330,95,29);
  text(s3,'r-squared','R² 0.368',885,401,330,49,37,true,blue);
  text(s3,'r-squared-reference','vs 0.197 for linear regression',885,460,330,70,23);
  text(s3,'paired-interval','Absolute MAE reduction: 3.04 cents\n95% paired bootstrap interval: 2.86 to 3.23 cents',64,569,1152,72,25);
  text(s3,'test-evaluation-footnote','11,191 test wallets. Bootstrap intervals condition on the fitted models and assume wallet independence.',64,666,1152,28,18,false,muted);
  s3.speakerNotes.text='On the held out wallets, the mean baseline has an average absolute error of 22.14 cents per share. Linear regression reduces this to 19.78 cents, and gradient boosting reduces it further to 16.74 cents. That is a 15.4 percent improvement over linear regression. The absolute difference is 3.04 cents, with a paired wallet-bootstrap interval from 2.86 to 3.23 cents. Boosting also has a higher R squared, about 0.368 compared with 0.197 for linear regression. The model comparison is consistent across MAE, RMSE, and R squared. These intervals describe uncertainty on the test wallets conditional on our fitted models. They assume independent wallets, which may be imperfect because wallets can trade in common markets.\n\nSources: tables/primary_model_metrics.csv; tables/paired_bootstrap_comparisons.csv; Figure 06. The editable chart preserves the point estimates. Individual-model MAE intervals and RMSE values remain in the comprehensive report. R² compares test squared error with variation around the test mean. No predictions are clipped in the main evaluation.';

  const s4=slide('Interpretation');
  const imp=S.importance.slice().reverse();
  const short={trade_count:'Trade count',total_notional:'Total spending',max_single_buy:'Largest purchase',unique_markets:'Markets traded',wallet_age_days:'Observed span',concentration:'Concentration'};
  s4.charts.add('bar',{
    position:{left:56,top:145,width:748,height:439},
    title:'Increase in MAE after shuffling (cents)',titleTextStyle:{fontSize:25,bold:true,fill:ink},
    categories:imp.map(r=>short[r.variable]),
    series:[{name:'Increase in MAE',values:imp.map(r=>Number(r.increase_MAE_cents.toFixed(8))),fill:blue}],
    barOptions:{direction:'bar',gapWidth:62},hasLegend:false,
    xAxis:{...axis,min:0,max:7,majorUnit:1,numberFormatCode:'0.0',majorGridlines:{fill:'#E8ECF1',width:1}},
    yAxis:{...axis,textStyle:{fontSize:22,fill:ink}},
    dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00',textStyle:{fontSize:21,bold:true,fill:ink}},
    chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'
  });
  text(s4,'reliance-takeaway','Trade count has the strongest model reliance.',851,161,360,124,31,true);
  text(s4,'ablation-takeaway','Removing spending and largest purchase raises MAE to 19.97 cents.',851,324,360,123,25);
  text(s4,'scope-caution','Same-period prediction.\nPrice differences can reflect market choice and timing.',851,491,360,118,24);
  text(s4,'attribution-caution','Correlated predictors limit attribution. Importance gives no effect direction or causal interpretation.',64,652,1150,34,20,false,muted);
  s4.speakerNotes.text='To interpret the flexible model, we shuffle one predictor at a time and measure the increase in test MAE. Trade count produces the largest increase, about 6.32 cents. Spending, largest purchase, and number of markets also contribute. This measures reliance by the fitted model, and it does not tell us whether an input raises or lowers price. Correlated predictors complicate attribution. In a sensitivity analysis, removing spending and largest purchase increases boosting error from 16.74 to 19.97 cents, so the monetary summaries add information. They are computed from the same observed trades as the target. The analysis therefore predicts differences across wallets within the observed history. Market choice and timing may explain part of those differences. We cannot infer profit, trading skill, future forecasting accuracy, or causal effects from this table.\n\nSources: tables/permutation_importance_test.csv; tables/all_model_metrics.csv; Figure 12 and Figure 14; https://scikit-learn.org/1.7/modules/permutation_importance.html. Native chart values are mean error increases over 20 shuffles. Shuffle standard deviations are in the comprehensive report and are not causal confidence intervals. The activity-only boosting comparison uses its own training-only search with the same grid. The confirmed flag is absent from the entire analysis.';
  return {slideCount:presentation.slides.items.length, titles:['Question and data','Approach','Results','Interpretation']};
}
