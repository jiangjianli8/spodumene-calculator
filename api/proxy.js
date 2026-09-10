/**
 * 锂辉石计价器 - 实时行情代理
 * Cloudflare Worker — 代理新浪财经 JSON API，添加 CORS 头
 *
 * 部署:
 *   npx wrangler deploy api/proxy.js
 */

// Sina 新浪财经 JSON API 配置
const SINA_API = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQFuturesData';
const SINA_PARAMS = new URLSearchParams({
  page: '1',
  sort: 'position',
  asc: '0',
  node: 'lc_qh',       // 碳酸锂品种代码
  base: 'futures',
});

// 简单内存缓存，避免同一秒内重复请求 Sina
const CACHE_TTL = 1500; // 1.5 秒
let cache = { data: null, ts: 0 };

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': '*',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // 路径: /lc → 返回碳酸锂主力合约
    const path = url.pathname.replace(/\/+$/, '');
    if (path !== '/lc' && path !== '') {
      return json({ error: 'Not Found', hint: 'Use /lc for carbonate lithium' }, 404);
    }

    // 缓存检查
    const now = Date.now();
    if (cache.data && (now - cache.ts) < CACHE_TTL) {
      return json(cache.data);
    }

    try {
      // 请求新浪 API
      const sinaResp = await fetch(`${SINA_API}?${SINA_PARAMS}`, {
        headers: {
          'Referer': 'https://finance.sina.com.cn/',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        },
      });

      if (!sinaResp.ok) {
        return json({ error: `Sina API returned ${sinaResp.status}` }, 502);
      }

      const contracts = await sinaResp.json();
      if (!Array.isArray(contracts) || contracts.length === 0) {
        return json({ error: 'No contract data from exchange' }, 502);
      }

      // 找 LC0（连续合约/主力合约）
      let item = contracts.find(c => c.symbol === 'LC0');
      if (!item) {
        item = contracts.reduce((a, b) =>
          (parseInt(a.volume) || 0) > (parseInt(b.volume) || 0) ? a : b
        );
      }

      const price = parseFloat(item.trade) || 0;
      const preClose = parseFloat(item.preclose) || 0;
      const changePct = parseFloat(item.changepercent) || 0;

      const result = {
        symbol: item.symbol || 'LC0',
        name: item.name || '碳酸锂',
        price: Math.round(price),
        open: Math.round(parseFloat(item.open) || 0),
        high: Math.round(parseFloat(item.high) || 0),
        low: Math.round(parseFloat(item.low) || 0),
        pre_close: Math.round(preClose),
        bid: Math.round(parseFloat(item.bidprice1) || 0),
        ask: Math.round(parseFloat(item.askprice1) || 0),
        volume: parseInt(item.volume) || 0,
        position: parseInt(item.position) || 0,
        change: Math.round(price - preClose),
        change_pct: Math.round(changePct * 100) / 100,
        date: item.tradedate || '',
        time: item.ticktime || '',
        status: '盘中实时',
        updated_at: new Date().toISOString(),
        features: {
          showFillBtn: true,
          refreshInterval: 5000,
          showBrandCard: true,
          showErrorDetail: true,
        },
      };

      // 更新缓存
      cache = { data: result, ts: now };

      return json(result);

    } catch (err) {
      return json({ error: 'Failed to fetch market data', detail: err.message }, 502);
    }
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
    },
  });
}
