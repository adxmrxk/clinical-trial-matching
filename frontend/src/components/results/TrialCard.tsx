'use client';

import { ClinicalTrial } from '@/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EligibilityBadge } from './EligibilityBadge';

interface TrialCardProps {
  trial: ClinicalTrial;
}

export function TrialCard({ trial }: TrialCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="text-xs font-mono">
                {trial.nctId}
              </Badge>
              {trial.phase && (
                <Badge variant="secondary" className="text-xs">
                  {trial.phase}
                </Badge>
              )}
            </div>
            <CardTitle className="text-base leading-tight">{trial.title}</CardTitle>
            <CardDescription className="mt-1">
              {trial.condition}
            </CardDescription>
          </div>
          <EligibilityBadge status={trial.eligibility} />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Key Details Grid */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-muted-foreground text-xs mb-0.5">Status</p>
            <p className="font-medium">{trial.status}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs mb-0.5">Location</p>
            <p className="font-medium">{trial.location}</p>
          </div>
          {trial.ageRange && (
            <div>
              <p className="text-muted-foreground text-xs mb-0.5">Age Range</p>
              <p className="font-medium">{trial.ageRange}</p>
            </div>
          )}
          {trial.sponsor && (
            <div>
              <p className="text-muted-foreground text-xs mb-0.5">Sponsor</p>
              <p className="font-medium truncate" title={trial.sponsor}>{trial.sponsor}</p>
            </div>
          )}
        </div>

        <Separator />

        {/* Brief Summary */}
        {trial.briefSummary && (
          <div>
            <p className="text-sm text-muted-foreground mb-1">About This Study</p>
            <p className="text-sm line-clamp-3">{trial.briefSummary}</p>
          </div>
        )}

        {/* Eligibility Explanation */}
        <div>
          <p className="text-sm text-muted-foreground mb-1">Eligibility Assessment</p>
          <p className="text-sm">{trial.explanation}</p>
        </div>

        {/* Criteria Sections */}
        {trial.criteriaMatched.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Criteria Met
            </p>
            <ul className="text-sm list-disc list-inside text-green-700 space-y-0.5">
              {trial.criteriaMatched.slice(0, 3).map((criteria, index) => (
                <li key={index} className="truncate" title={criteria}>{criteria}</li>
              ))}
              {trial.criteriaMatched.length > 3 && (
                <li className="text-muted-foreground">+{trial.criteriaMatched.length - 3} more</li>
              )}
            </ul>
          </div>
        )}

        {trial.criteriaViolated.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
              <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Criteria Not Met
            </p>
            <ul className="text-sm list-disc list-inside text-red-700 space-y-0.5">
              {trial.criteriaViolated.slice(0, 3).map((criteria, index) => (
                <li key={index} className="truncate" title={criteria}>{criteria}</li>
              ))}
              {trial.criteriaViolated.length > 3 && (
                <li className="text-muted-foreground">+{trial.criteriaViolated.length - 3} more</li>
              )}
            </ul>
          </div>
        )}

        {trial.criteriaUnknown.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
              <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              More Information Needed
            </p>
            <ul className="text-sm list-disc list-inside text-yellow-700 space-y-0.5">
              {trial.criteriaUnknown.slice(0, 3).map((criteria, index) => (
                <li key={index} className="truncate" title={criteria}>{criteria}</li>
              ))}
              {trial.criteriaUnknown.length > 3 && (
                <li className="text-muted-foreground">+{trial.criteriaUnknown.length - 3} more</li>
              )}
            </ul>
          </div>
        )}

        <Separator />

        {/* Contact Info */}
        {(trial.contactName || trial.contactEmail || trial.contactPhone) && (
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-sm font-medium mb-2">Contact Information</p>
            <div className="text-sm space-y-1">
              {trial.contactName && <p>{trial.contactName}</p>}
              {trial.contactEmail && (
                <p>
                  <a href={`mailto:${trial.contactEmail}`} className="text-primary hover:underline">
                    {trial.contactEmail}
                  </a>
                </p>
              )}
              {trial.contactPhone && <p>{trial.contactPhone}</p>}
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="flex gap-2">
          <Button asChild className="flex-1">
            <a href={trial.officialUrl} target="_blank" rel="noopener noreferrer">
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              View on ClinicalTrials.gov
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
