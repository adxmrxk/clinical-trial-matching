'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiService } from '@/lib/api';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSendMessage, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Use webm format which is widely supported
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());

        if (chunksRef.current.length === 0) {
          setIsRecording(false);
          return;
        }

        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });

        // Send to backend for transcription
        setIsTranscribing(true);
        try {
          const text = await apiService.transcribeAudio(audioBlob);
          if (text && text.trim()) {
            setInput(prev => prev ? `${prev} ${text}` : text);
          }
        } catch (error) {
          console.error('Transcription error:', error);
        } finally {
          setIsTranscribing(false);
          setIsRecording(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleSend = () => {
    if (input.trim() && !disabled) {
      // Stop recording if active
      if (isRecording) {
        stopRecording();
      }
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getPlaceholder = () => {
    if (isTranscribing) return "Transcribing...";
    if (isRecording) return "Recording... Click stop when done";
    return "Type your message or click the microphone...";
  };

  return (
    <div className="flex gap-2 p-4 border-t bg-background">
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={getPlaceholder()}
        disabled={disabled || isTranscribing}
        className={`flex-1 border border-black/20 ${isRecording ? 'border-red-500 bg-red-50' : ''} ${isTranscribing ? 'bg-gray-50' : ''}`}
      />

      {/* Microphone Button */}
      <Button
        type="button"
        variant={isRecording ? "destructive" : "outline"}
        onClick={toggleRecording}
        disabled={disabled || isTranscribing}
        className={`px-3 ${isRecording ? 'animate-pulse' : ''}`}
        title={isRecording ? "Stop recording" : "Start voice input"}
      >
        {isTranscribing ? (
          // Loading spinner
          <svg className="animate-spin" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
            <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
          </svg>
        ) : isRecording ? (
          // Stop icon (square)
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        ) : (
          // Microphone icon
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" x2="12" y1="19" y2="22"/>
          </svg>
        )}
      </Button>

      {/* Send Button */}
      <Button onClick={handleSend} disabled={disabled || !input.trim() || isTranscribing}>
        Send
      </Button>
    </div>
  );
}
