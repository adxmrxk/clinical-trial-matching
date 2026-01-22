'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

export function EthicalDisclaimer() {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) {
    return null;
  }

  return (
    <div className="bg-muted border-b px-4 py-3">
      <div className="max-w-4xl mx-auto flex items-start gap-4">
        <div className="flex-1">
          <p className="text-sm font-medium">Important Medical Disclaimer</p>
          <p className="text-sm text-muted-foreground mt-1">
            This tool is for informational purposes only and does not provide medical advice.
            Clinical trial eligibility shown here is preliminary and must be confirmed by healthcare
            providers and trial coordinators. Always consult with your doctor before making any
            decisions about participating in clinical trials.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsDismissed(true)}
          className="shrink-0"
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}
