'use client';

import { useCallback, useLayoutEffect, useRef, useState } from 'react';

type Option<T extends string> = { value: T; label: string };

type SegmentedFilterProps<T extends string> = {
  value: T;
  onValueChange: (next: T) => void;
  options: readonly Option<T>[];
  className?: string;
  'aria-label'?: string;
};

function cx(...parts: Array<string | false | undefined | null>) {
  return parts.filter(Boolean).join(' ');
}

/**
 * Segmented control: pill nền muted + nền trượt (ease mượt), chữ/hover/scale trên mục chưa chọn,
 * focus ring; `motion-reduce` rút thời gian chuyển động.
 */
export function SegmentedFilter<T extends string>({
  value,
  onValueChange,
  options,
  className,
  'aria-label': ariaLabel,
}: SegmentedFilterProps<T>) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const btnRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [hl, setHl] = useState<{ left: number; width: number }>({ left: 0, width: 0 });

  const optionSig = options.map((o) => `${o.value}:${o.label}`).join('\u001f');

  const measure = useCallback(() => {
    const root = containerRef.current;
    const btn = btnRefs.current.get(value);
    if (!root || !btn) return;
    const rr = root.getBoundingClientRect();
    const br = btn.getBoundingClientRect();
    setHl({ left: br.left - rr.left, width: br.width });
  }, [value, optionSig]);

  useLayoutEffect(() => {
    measure();
    const id = requestAnimationFrame(() => measure());
    return () => cancelAnimationFrame(id);
  }, [measure]);

  useLayoutEffect(() => {
    const root = containerRef.current;
    if (!root || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => measure());
    ro.observe(root);
    return () => ro.disconnect();
  }, [measure]);

  useLayoutEffect(() => {
    const onResize = () => measure();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [measure]);

  return (
    <div
      ref={containerRef}
      role="tablist"
      aria-label={ariaLabel}
      className={cx(
        'relative inline-flex h-10 shrink-0 items-stretch gap-0 overflow-hidden rounded-full border border-border/60 bg-muted/60 p-1 text-sm',
        'transition-[box-shadow] duration-300 ease-out hover:shadow-sm motion-reduce:transition-none',
        className,
      )}
    >
      <span
        aria-hidden
        className={cx(
          'pointer-events-none absolute top-1 bottom-1 rounded-full bg-background shadow-sm ring-1 ring-black/5 will-change-[left,width] dark:ring-white/10',
          'transition-[left,width,opacity,box-shadow] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
          'motion-reduce:duration-150 motion-reduce:ease-linear motion-reduce:transition-[left,width,opacity]',
          hl.width > 0 ? 'opacity-100' : 'opacity-0',
        )}
        style={{ left: hl.left, width: hl.width }}
      />
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            ref={(el) => {
              const m = btnRefs.current;
              if (el) m.set(opt.value, el);
              else m.delete(opt.value);
            }}
            type="button"
            role="tab"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onValueChange(opt.value)}
            className={cx(
              'relative z-10 min-w-[3.25rem] rounded-full px-3.5 py-1.5 font-medium sm:min-w-0 sm:px-4',
              'transition-[color,background-color,opacity,transform] duration-300 ease-out',
              'motion-reduce:transition-colors motion-reduce:duration-150 motion-reduce:hover:transform-none',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
              active
                ? 'text-foreground opacity-100'
                : 'text-muted-foreground opacity-90 hover:text-foreground hover:opacity-100 hover:bg-background/25 hover:scale-[1.02] active:scale-[0.98] dark:hover:bg-background/15',
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
