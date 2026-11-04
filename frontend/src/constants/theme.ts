/**
 * PhysioBand AI design tokens - light theme only.
 * Palette taken from the PhysioBand AI logo: deep navy plate, electric teal arc and
 * green resistance band, used on a soft cool-white canvas.
 */
export const colors = {
  background: '#F3F7FB',
  backgroundAlt: '#EAF1F8',
  surface: '#FFFFFF',
  surfaceMuted: '#F7FAFD',
  border: '#E1E8F1',
  borderStrong: '#C9D5E3',

  text: '#0A1B33',
  textSecondary: '#44546B',
  textMuted: '#8F9DB2',
  textOnPrimary: '#FFFFFF',

  navy: '#021C40',
  navyLight: '#063862',
  teal: '#00FAD8', // logo accent - only on navy backgrounds (too bright for text on white)

  primary: '#00A396',
  primaryDark: '#007A73',
  primarySoft: '#C2F5EC',
  primaryTint: '#EBFCF8',
  accent: '#3D5AFE',
  accentSoft: '#E3E8FF',

  success: '#16C060',
  successSoft: '#D7F8E4',
  warning: '#F59E0B',
  warningSoft: '#FEF3C7',
  danger: '#EF4444',
  dangerSoft: '#FEE2E2',
  info: '#3B82F6',
  infoSoft: '#DBEAFE',
  coral: '#FB7185',
  coralSoft: '#FFE4E6',
};

export const gradients = {
  primary: ['#00C2AE', '#00978F', '#05607A'] as const,
  hero: ['#063862', '#03264D', '#011536'] as const,
  accent: ['#6B82FF', '#3D5AFE'] as const,
  soft: ['#EBFCF8', '#EAF1FA'] as const,
  sunrise: ['#FDBA74', '#FB7185'] as const,
};

/** Colour per movement-quality class (matches backend labels). */
export const qualityColors: Record<string, { fg: string; bg: string; icon: string }> = {
  correct: { fg: colors.success, bg: colors.successSoft, icon: 'checkmark-circle' },
  incomplete: { fg: colors.warning, bg: colors.warningSoft, icon: 'remove-circle' },
  too_fast: { fg: colors.coral, bg: colors.coralSoft, icon: 'speedometer' },
  irregular: { fg: colors.accent, bg: colors.accentSoft, icon: 'pulse' },
  unclassified: { fg: colors.textMuted, bg: colors.surfaceMuted, icon: 'help-circle' },
};

export const fonts = {
  regular: 'Inter_400Regular',
  medium: 'Inter_500Medium',
  semibold: 'Inter_600SemiBold',
  bold: 'Inter_700Bold',
  extrabold: 'Inter_800ExtraBold',
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 28, xxxl: 40 };
export const radius = { sm: 8, md: 12, lg: 16, xl: 22, xxl: 28, pill: 999 };

export const shadow = {
  card: {
    shadowColor: '#0F172A',
    shadowOpacity: 0.06,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
  raised: {
    shadowColor: '#021C40',
    shadowOpacity: 0.25,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 8,
  },
};

export const type = {
  display: { fontFamily: fonts.extrabold, fontSize: 34, letterSpacing: -0.8, color: colors.text },
  h1: { fontFamily: fonts.bold, fontSize: 26, letterSpacing: -0.5, color: colors.text },
  h2: { fontFamily: fonts.bold, fontSize: 20, letterSpacing: -0.3, color: colors.text },
  h3: { fontFamily: fonts.semibold, fontSize: 16, color: colors.text },
  body: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22, color: colors.textSecondary },
  bodyStrong: { fontFamily: fonts.semibold, fontSize: 15, color: colors.text },
  caption: { fontFamily: fonts.medium, fontSize: 12, color: colors.textMuted },
  label: { fontFamily: fonts.semibold, fontSize: 12, letterSpacing: 0.6, color: colors.textMuted, textTransform: 'uppercase' as const },
};
