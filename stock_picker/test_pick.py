import os
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
from stock_picker import run_stock_pick

print('=== 测试完整选股流程 ===')
selected = run_stock_pick()
print(f'最终选中 {len(selected)} 只股票')
for s in selected:
    print(f"  {s['name']}({s['code']}) 价格:{s['price']} 涨幅:{s['change_pct']}% 换手:{s['turnover']}%")
