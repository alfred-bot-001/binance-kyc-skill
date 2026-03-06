// i18n — Chinese / English toggle
let currentLang = 'en';

const translations = {
  'header.title': { en: '🔐 Binance KYC — Chat Verification', zh: '🔐 币安 KYC — 聊天式身份验证' },
  'header.subtitle': { en: 'Complete identity verification without leaving the chat', zh: '无需离开聊天即可完成身份验证' },
  'nav.demo': { en: '💬 Chat Demo', zh: '💬 聊天演示' },
  'nav.business': { en: '💼 Business', zh: '💼 商业分析' },
  'nav.tech': { en: '🔧 Technical', zh: '🔧 技术架构' },
  'chat.title': { en: 'Binance KYC Bot', zh: '币安 KYC 机器人' },
  'chat.online': { en: 'Online', zh: '在线' },
  'chat.placeholder': { en: 'Type a message...', zh: '输入消息...' },
  'chat.photo': { en: '📷', zh: '📷' },
  'chat.send': { en: '→', zh: '→' },
  'info.flow': { en: '📋 Verification Flow', zh: '📋 验证流程' },
  'info.collected': { en: '📝 Collected Data', zh: '📝 已收集数据' },
  'info.comparison': { en: '⚡ vs Traditional KYC', zh: '⚡ 对比传统 KYC' },
  'info.name': { en: 'Full Name', zh: '姓名' },
  'info.dob': { en: 'Date of Birth', zh: '出生日期' },
  'info.nationality': { en: 'Nationality', zh: '国籍' },
  'info.address': { en: 'Address', zh: '地址' },
  'info.document': { en: 'Document', zh: '证件' },
  'biz.market.title': { en: '📊 Market Opportunity', zh: '📊 市场机会' },
  'biz.scenarios.title': { en: '💡 Business Scenarios', zh: '💡 业务场景' },
  'biz.compare.title': { en: '⚔️ Competitive Analysis', zh: '⚔️ 竞品分析' },
  'biz.calc.title': { en: '🧮 ROI Calculator', zh: '🧮 ROI 计算器' },
  'biz.risk.title': { en: '⚠️ Risk Assessment', zh: '⚠️ 风险评估' },
};

function t(key) {
  const entry = translations[key];
  return entry ? (entry[currentLang] || entry['en']) : key;
}

function toggleLang() {
  currentLang = currentLang === 'en' ? 'zh' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  const btn = document.querySelector('.lang-toggle');
  if (btn) btn.textContent = currentLang === 'en' ? '中文' : 'EN';
  if (typeof onLangChange === 'function') onLangChange(currentLang);
}
