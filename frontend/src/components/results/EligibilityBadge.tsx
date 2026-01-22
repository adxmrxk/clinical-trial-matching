'use client';

import { Badge } from '@/components/ui/badge';
import { EligibilityStatus } from '@/types';
import { cn } from '@/lib/utils';

interface EligibilityBadgeProps {
  status: EligibilityStatus;
}

const statusConfig = {
  eligible: {
    label: 'Eligible',
    className: 'bg-green-100 text-green-800 hover:bg-green-100',
  },
  ineligible: {
    label: 'Ineligible',
    className: 'bg-red-100 text-red-800 hover:bg-red-100',
  },
  uncertain: {
    label: 'Uncertain',
    className: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
  },
};

export function EligibilityBadge({ status }: EligibilityBadgeProps) {
  const config = statusConfig[status];

  return (
    <Badge variant="secondary" className={cn(config.className)}>
      {config.label}
    </Badge>
  );
}
