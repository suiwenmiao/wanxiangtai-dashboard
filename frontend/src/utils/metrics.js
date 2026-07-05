export function sumMetrics(records) {
  const total = records.reduce(
    (acc, row) => {
      acc.cost += row.cost || 0;
      acc.totalSales += row.totalSales || 0;
      acc.directSales += row.directSales || 0;
      acc.orders += row.orders || 0;
      acc.clicks += row.clicks || 0;
      acc.impressions += row.impressions || 0;
      acc.carts += row.carts || 0;
      return acc;
    },
    {
      cost: 0,
      totalSales: 0,
      directSales: 0,
      orders: 0,
      clicks: 0,
      impressions: 0,
      carts: 0
    }
  );

  return {
    ...total,
    directRoi: total.cost > 0 ? total.directSales / total.cost : 0,
    totalRoi: total.cost > 0 ? total.totalSales / total.cost : 0,
    cvr: total.clicks > 0 ? total.orders / total.clicks : 0,
    ctr: total.impressions > 0 ? total.clicks / total.impressions : 0,
    cpc: total.clicks > 0 ? total.cost / total.clicks : 0
  };
}

export function groupBy(records, key) {
  return records.reduce((map, row) => {
    const value = row[key] || "其他";
    if (!map.has(value)) map.set(value, []);
    map.get(value).push(row);
    return map;
  }, new Map());
}

export function formatMoney(value) {
  const number = Number(value || 0);
  if (Math.abs(number) >= 100000000) return `${(number / 100000000).toFixed(2)}亿`;
  if (Math.abs(number) >= 10000) return `${(number / 10000).toFixed(2)}万`;
  return number.toFixed(0);
}

export function formatPercent(value) {
  return `${((value || 0) * 100).toFixed(2)}%`;
}

export function byDate(records) {
  const groups = groupBy(records, "date");
  return Array.from(groups.entries())
    .map(([date, rows]) => ({
      date,
      ...sumMetrics(rows)
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function byCategory(records) {
  const groups = groupBy(records, "category");
  return Array.from(groups.entries())
    .map(([category, rows]) => ({
      category,
      ...sumMetrics(rows)
    }))
    .sort((a, b) => b.cost - a.cost);
}
