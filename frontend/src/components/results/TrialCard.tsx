'use client';

import { ClinicalTrial } from '@/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { EligibilityBadge } from './EligibilityBadge';

interface TrialCardProps {
  trial: ClinicalTrial;
}

export function TrialCard({ trial }: TrialCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <CardTitle className="text-base leading-tight">{trial.title}</CardTitle>
            <CardDescription className="mt-1">
              {trial.condition} | {trial.location}
            </CardDescription>
          </div>
          <EligibilityBadge status={trial.eligibility} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-sm text-muted-foreground mb-1">Status</p>
          <p className="text-sm font-medium">{trial.status}</p>
        </div>

        <Separator />

        <div>
          <p className="text-sm text-muted-foreground mb-1">Eligibility Explanation</p>
          <p className="text-sm">{trial.explanation}</p>
        </div>

        {trial.criteriaMatched.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-1">Criteria Met</p>
            <ul className="text-sm list-disc list-inside text-green-700">
              {trial.criteriaMatched.map((criteria, index) => (
                <li key={index}>{criteria}</li>
              ))}
            </ul>
          </div>
        )}

        {trial.criteriaViolated.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-1">Criteria Not Met</p>
            <ul className="text-sm list-disc list-inside text-red-700">
              {trial.criteriaViolated.map((criteria, index) => (
                <li key={index}>{criteria}</li>
              ))}
            </ul>
          </div>
        )}

        {trial.criteriaUnknown.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-1">More Information Needed</p>
            <ul className="text-sm list-disc list-inside text-yellow-700">
              {trial.criteriaUnknown.map((criteria, index) => (
                <li key={index}>{criteria}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
