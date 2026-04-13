'use client';

import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';

export type ListSearchInputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  id?: string;
  'aria-label'?: string;
  disabled?: boolean;
  /** Appended to the default wrapper: `relative w-full max-w-sm min-w-0` */
  className?: string;
  /** Appended to the input `pl-10` */
  inputClassName?: string;
};

/**
 * Standard list search field: fixed max width, icon inset left (lucide Search).
 * Use beside a Select filter in a `flex flex-col gap-4 sm:flex-row sm:items-center` row.
 */
export function ListSearchInput({
  value,
  onChange,
  placeholder,
  id,
  'aria-label': ariaLabel,
  disabled,
  className,
  inputClassName,
}: ListSearchInputProps) {
  const wrap = `relative w-full max-w-sm min-w-0${className ? ` ${className}` : ''}`;
  const inputCls = `pl-10${inputClassName ? ` ${inputClassName}` : ''}`;
  return (
    <div className={wrap}>
      <Search
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden
      />
      <Input
        id={id}
        aria-label={ariaLabel}
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={inputCls}
      />
    </div>
  );
}
