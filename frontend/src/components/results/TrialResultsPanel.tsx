'use client';

import { useState } from 'react';
import { ClinicalTrial } from '@/types';
import { TrialCard } from './TrialCard';
import { Button } from '@/components/ui/button';

interface TrialResultsPanelProps {
  trials: ClinicalTrial[];
}

export function TrialResultsPanel({ trials }: TrialResultsPanelProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState<'left' | 'right'>('right');
  const [isAnimating, setIsAnimating] = useState(false);

  if (trials.length === 0) {
    return null;
  }

  const goToPrevious = () => {
    if (isAnimating) return;
    setDirection('left');
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev === 0 ? trials.length - 1 : prev - 1));
      setIsAnimating(false);
    }, 300);
  };

  const goToNext = () => {
    if (isAnimating) return;
    setDirection('right');
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev === trials.length - 1 ? 0 : prev + 1));
      setIsAnimating(false);
    }, 300);
  };

  const currentTrial = trials[currentIndex];

  return (
    <div className="border rounded-lg bg-card overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h2 className="font-semibold">Matching Clinical Trials</h2>
          <p className="text-sm text-muted-foreground">
            Showing {currentIndex + 1} of {trials.length} trials
          </p>
        </div>

        {/* Navigation Arrows */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={goToPrevious}
            disabled={isAnimating}
            className="h-8 w-8 p-0"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={goToNext}
            disabled={isAnimating}
            className="h-8 w-8 p-0"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Button>
        </div>
      </div>

      {/* Card Container with Animation */}
      <div className="p-4 relative overflow-hidden">
        <div
          className={`transition-all duration-300 ease-in-out ${
            isAnimating
              ? direction === 'right'
                ? '-translate-x-4 opacity-0'
                : 'translate-x-4 opacity-0'
              : 'translate-x-0 opacity-100'
          }`}
        >
          <TrialCard trial={currentTrial} />
        </div>
      </div>

      {/* Dot Indicators */}
      <div className="px-4 pb-4 flex justify-center gap-2">
        {trials.map((_, index) => (
          <button
            key={index}
            onClick={() => {
              if (isAnimating || index === currentIndex) return;
              setDirection(index > currentIndex ? 'right' : 'left');
              setIsAnimating(true);
              setTimeout(() => {
                setCurrentIndex(index);
                setIsAnimating(false);
              }, 300);
            }}
            className={`h-2 rounded-full transition-all duration-300 ${
              index === currentIndex
                ? 'w-6 bg-primary'
                : 'w-2 bg-muted-foreground/30 hover:bg-muted-foreground/50'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
