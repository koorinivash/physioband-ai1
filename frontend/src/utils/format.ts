import { colors } from '../constants/theme';

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  const rest = s % 60;
  return m > 0 ? `${m}m ${rest.toString().padStart(2, '0')}s` : `${rest}s`;
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: d.getFullYear() === today.getFullYear() ? undefined : 'numeric' });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export function shortDay(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00`);
  return d.toLocaleDateString(undefined, { weekday: 'short' }).slice(0, 3);
}

export function formatNumber(v: number | null | undefined, digits = 1, unit = ''): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return `${v.toFixed(digits)}${unit}`;
}

export function qualityTone(score: number | null | undefined): { fg: string; bg: string; label: string } {
  if (score === null || score === undefined) return { fg: colors.textMuted, bg: colors.surfaceMuted, label: 'No score' };
  if (score >= 80) return { fg: colors.success, bg: colors.successSoft, label: 'Excellent' };
  if (score >= 60) return { fg: colors.primary, bg: colors.primaryTint, label: 'Good' };
  if (score >= 40) return { fg: colors.warning, bg: colors.warningSoft, label: 'Needs work' };
  return { fg: colors.danger, bg: colors.dangerSoft, label: 'Keep practising' };
}

export function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export function firstName(name: string | undefined): string {
  return (name ?? '').trim().split(/\s+/)[0] || 'there';
}

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
