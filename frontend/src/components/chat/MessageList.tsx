'use client';

import { useEffect, useRef } from 'react';
import { Message } from '@/types';
import { ChatMessage } from './ChatMessage';
import { ScrollArea } from '@/components/ui/scroll-area';

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
}

// Loading animation component
function LoadingIndicator() {
  return (
    <div className="flex items-start gap-3 animate-in fade-in duration-300">
      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
        <svg className="w-5 h-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" x2="12" y1="19" y2="22"/>
        </svg>
      </div>
      <div className="bg-muted rounded-lg px-4 py-3 max-w-[80%]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
            <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
            <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce"></span>
          </div>
          <span className="text-sm text-muted-foreground ml-2">Processing your request...</span>
        </div>
      </div>
    </div>
  );
}

export function MessageList({ messages, isLoading = false }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-4">
        {messages.length === 0 && !isLoading ? (
          <div className="flex flex-col items-center justify-center text-center text-muted-foreground py-12">
            <h3 className="text-lg font-medium mb-2">Welcome to Clinical Trial Matcher</h3>
            <p className="max-w-md">
              Tell me about your medical condition, and I&apos;ll help you find relevant clinical trials.
              You can share details like your diagnosis, age, current medications, and location.
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isLoading && <LoadingIndicator />}
          </>
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
