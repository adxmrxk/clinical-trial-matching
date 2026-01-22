'use client';

import { useState } from 'react';
import { ClinicalTrial } from '@/types';
import { ChatContainer } from '@/components/chat';
import { TrialResultsPanel } from '@/components/results';
import { EthicalDisclaimer } from '@/components/disclaimer';

export default function Home() {
  const [trials, setTrials] = useState<ClinicalTrial[]>([]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-secondary">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-xl font-bold text-primary">Clinical Trial Matcher</h1>
          <p className="text-sm text-muted-foreground">
            AI-powered clinical trial matching system
          </p>
        </div>
      </header>

      {/* Ethical Disclaimer */}
      <EthicalDisclaimer />

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6 space-y-6">
        {/* Chat Section */}
        <section className="h-[500px]">
          <ChatContainer onTrialsFound={setTrials} />
        </section>

        {/* Results Section */}
        <section>
          <TrialResultsPanel trials={trials} />
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t bg-secondary">
        <div className="max-w-4xl mx-auto px-4 py-4 text-center text-sm text-muted-foreground">
          <p>
            This tool is for research purposes only. Always consult healthcare
            professionals for medical decisions.
          </p>
        </div>
      </footer>
    </div>
  );
}
