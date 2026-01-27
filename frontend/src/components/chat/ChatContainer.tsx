'use client';

import { useState } from 'react';
import { Message, ClinicalTrial } from '@/types';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { apiService } from '@/lib/api';
import { getMockResponse, mockTrials } from '@/lib/mockData';

interface ChatContainerProps {
  onTrialsFound: (trials: ClinicalTrial[]) => void;
}

// Set to true to use real backend, false for mock data
const USE_REAL_API = process.env.NEXT_PUBLIC_USE_REAL_API === 'true';

export function ChatContainer({ onTrialsFound }: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let responseContent: string;
      let trials: ClinicalTrial[] = [];

      if (USE_REAL_API) {
        // Use real backend API
        const result = await apiService.sendMessage(content);
        responseContent = result.response;
        trials = result.trials;
      } else {
        // Use mock data for development
        await new Promise((resolve) => setTimeout(resolve, 1000));
        responseContent = getMockResponse(content);

        // Show mock trials after a few messages
        if (messages.length >= 2) {
          trials = mockTrials;
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (trials.length > 0) {
        onTrialsFound(trials);
      }
    } catch (error) {
      console.error('Error sending message:', error);

      // Fallback to mock on error
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I'm having trouble connecting to the server. Please try again in a moment.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full border rounded-lg bg-card overflow-hidden">
      <div className="p-4 border-b shrink-0">
        <h2 className="font-semibold">Chat with Clinical Trial Assistant</h2>
        <p className="text-sm text-muted-foreground">
          Share your health information to find matching clinical trials
        </p>
      </div>
      <div className="flex-1 overflow-hidden min-h-0">
        <MessageList messages={messages} isLoading={isLoading} />
      </div>
      <div className="shrink-0">
        <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}
