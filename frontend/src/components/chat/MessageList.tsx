'use client';

import { useEffect, useRef } from 'react';
import { Message } from '@/types';
import { ChatMessage } from './ChatMessage';
import { ScrollArea } from '@/components/ui/scroll-area';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <ScrollArea className="flex-1 p-4">
      <div className="flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground py-12">
            <h3 className="text-lg font-medium mb-2">Welcome to Clinical Trial Matcher</h3>
            <p className="max-w-md">
              Tell me about your medical condition, and I&apos;ll help you find relevant clinical trials.
              You can share details like your diagnosis, age, current medications, and location.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
