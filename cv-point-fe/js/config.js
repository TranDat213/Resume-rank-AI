// js/config.js
// Chỉnh URL này nếu NestJS chạy ở port khác

const API = 'http://localhost:3000';

const ENDPOINTS = {
  login:    `${API}/auth/login`,
  register: `${API}/auth/register`,
  health:   `${API}/health`,
  rank:     `${API}/ranking/upload`,
};