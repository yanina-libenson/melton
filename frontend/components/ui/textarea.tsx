import * as React from 'react'

import { cn } from '@/lib/utils'

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'border-input placeholder:text-muted-foreground bg-background shadow-soft-xs flex field-sizing-content min-h-24 w-full rounded-lg border px-4 py-3 text-base transition-all duration-200 ease-out outline-none disabled:cursor-not-allowed disabled:opacity-50',
        'hover:border-accent-foreground/20 hover:shadow-soft-sm',
        'focus:border-ring focus:ring-ring/20 focus:shadow-soft-sm focus:ring-2',
        'aria-invalid:ring-destructive/20 aria-invalid:border-destructive',
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
