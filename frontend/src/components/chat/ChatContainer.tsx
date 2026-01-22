'use client';

import { useState } from 'react';
import { Message, ClinicalTrial } from '@/types';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { getMockResponse, mockTrials } from '@/lib/mockData';

interface ChatContainerProps {
  onTrialsFound: (trials: ClinicalTrial[]) => void;
}

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

    // Simulate AI response delay
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const response = getMockResponse(content);
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsLoading(false);

    // After a few messages, show trial results
    if (messages.length >= 2) {
      onTrialsFound(mockTrials);
    }
  };

  return (
    <div className="flex flex-col h-full border rounded-lg bg-card">
      <div className="p-4 border-b">
        <h2 className="font-semibold">Chat with Clinical Trial Assistant</h2>
        <p className="text-sm text-muted-foreground">
          Share your health information to find matching clinical trials
        </p>
      </div>
      <MessageList messages={messages} />
      <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  );
}
