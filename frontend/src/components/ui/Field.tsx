import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

const control =
  'rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-800 shadow-xs focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none'

export function Select({ label, children, className = '', ...rest }: SelectHTMLAttributes<HTMLSelectElement> & { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
      {label}
      <select className={`${control} ${className}`} {...rest}>
        {children}
      </select>
    </label>
  )
}

export function Input({ label, className = '', ...rest }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
      {label}
      <input className={`${control} ${className}`} {...rest} />
    </label>
  )
}

export function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-700 select-none">
      <input type="checkbox" className="h-4 w-4 rounded border-slate-300 accent-primary" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  )
}
