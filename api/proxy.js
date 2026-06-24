/**
 * Cloudflare Worker - CORS proxy for Sina futures API
 */
const API = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQFuturesData';
const PARAMS = 'page=1&sort=position&asc=0&node=lc_qh&base=futures';
let cache = { d: null, t: 0 };

export default {
  async fetch(r) {
    const u = new URL(r.url);
    if (r.method === 'OPTIONS') return new Response(null, { status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,OPTIONS', 'Access-Control-Allow-Headers': '*', 'Access-Control-Max-Age': '86400' } });
    if (u.pathname.replace(/\/+$/, '') !== '/lc' && u.pathname !== '') return j({ e: 'Not Found' }, 404);
    const n = Date.now();
    if (cache.d && (n - cache.t) < 1500) return j(cache.d);
    try {
      const res = await fetch(API + '?' + PARAMS, { headers: { 'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0' } });
      if (!res.ok) return j({ e: 'Upstream ' + res.status }, 502);
      const arr = await res.json();
      if (!arr || !arr.length) return j({ e: 'No data' }, 502);
      let item = arr.find(c => c.symbol === 'LC0') || arr.reduce((a, b) => (+a.volume || 0) > (+b.volume || 0) ? a : b);
      const p = +item.trade || 0, pc = +item.preclose || 0, cp = +item.changepercent || 0;
      const out = { symbol: item.symbol || 'LC0', name: item.name || '', price: Math.round(p), open: Math.round(+item.open || 0), high: Math.round(+item.high || 0), low: Math.round(+item.low || 0), pre_close: Math.round(pc), bid: Math.round(+item.bidprice1 || 0), ask: Math.round(+item.askprice1 || 0), volume: +item.volume || 0, position: +item.position || 0, change: Math.round(p - pc), change_pct: Math.round(cp * 100) / 100, date: item.tradedate || '', time: item.ticktime || '', status: (+item.close === 0 && p > 0) ? '盘中实时' : '收盘', updated_at: new Date().toISOString() };
      cache = { d: out, t: n };
      return j(out);
    } catch (e) { return j({ e: 'Fetch failed', d: e.message }, 502); }
  }
};
function j(d, s) { return new Response(JSON.stringify(d), { status: s || 200, headers: { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-cache' } }); }