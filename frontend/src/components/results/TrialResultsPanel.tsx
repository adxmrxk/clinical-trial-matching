'use client';

import { useState } from 'react';
import { ClinicalTrial } from '@/types';
import { TrialCard } from './TrialCard';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface TrialResultsPanelProps {
  trials: ClinicalTrial[];
}

export function TrialResultsPanel({ trials }: TrialResultsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (trials.length === 0) {
    return null;
  }

  const eligibleCount = trials.filter((t) => t.eligibility === 'eligible').length;
  const uncertainCount = trials.filter((t) => t.eligibility === 'uncertain').length;

  return (
    <div className="border rounded-lg bg-card">
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h2 className="font-semibold">Matching Clinical Trials</h2>
          <p className="text-sm text-muted-foreground">
            Found {trials.length} trials ({eligibleCount} eligible, {uncertainCount} need more info)
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? 'Collapse' : 'Expand'}
        </Button>
      </div>

      {isExpanded && (
        <ScrollArea className="max-h-[500px]">
          <div className="p-4 grid gap-4">
            {trials.map((trial) => (
              <TrialCard key={trial.id} trial={trial} />
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
