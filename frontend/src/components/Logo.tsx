import React from 'react';
import { Image, View } from 'react-native';

import { colors } from '../constants/theme';

const LOGO = require('../../assets/logo.png');

/** Official PhysioBand AI logo (navy rounded plate with transparent corners). */
export function LogoMark({ size = 64 }: { size?: number }) {
  return <Image source={LOGO} style={{ width: size, height: size }} resizeMode="contain" accessibilityLabel="PhysioBand AI logo" />;
}

/** Logo with a soft shadow; `ring` adds a teal outline so it stands out on navy backgrounds. */
export function LogoBadge({ size = 40, ring = false }: { size?: number; ring?: boolean }) {
  return (
    <View
      style={[
        { alignSelf: 'flex-start', borderRadius: size * 0.24, shadowColor: colors.navy, shadowOpacity: 0.3, shadowRadius: 10, shadowOffset: { width: 0, height: 6 }, elevation: 6 },
        ring && { padding: 3, borderWidth: 1.5, borderColor: 'rgba(0,250,216,0.55)', backgroundColor: 'rgba(0,250,216,0.08)' },
      ]}
    >
      <LogoMark size={size} />
    </View>
  );
}
