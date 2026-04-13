/**
 * Recharts defaults use mid-gray (#666) for ticks and legend text, which disappears on dark backgrounds.
 * Use theme tokens so charts stay readable in light and dark mode.
 */
export const RECHARTS_TICK = { fontSize: 11, fill: 'hsl(var(--foreground))' } as const;

export const RECHARTS_TICK_MD = { fontSize: 12, fill: 'hsl(var(--foreground))' } as const;

export const RECHARTS_LEGEND_WRAPPER_STYLE = {
  color: 'hsl(var(--foreground))',
  fontSize: 12,
} as const;

export const RECHARTS_GRID_STROKE = 'hsl(var(--border))';
