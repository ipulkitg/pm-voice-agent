'use client';

import { useEffect, useRef, useMemo } from 'react';
import { Room } from 'livekit-client';
import {
  type ReceivedChatMessage,
  type TextStreamData,
  useRoomContext,
  useTranscriptions,
} from '@livekit/components-react';
import { ChatEntry } from '@/components/livekit/chat-entry';
import { cn } from '@/lib/utils';
import { ScrollArea } from '../livekit/scroll-area/scroll-area';

function transcriptionToChatMessage(textStream: TextStreamData, room: Room): ReceivedChatMessage {
  return {
    id: textStream.streamInfo.id,
    timestamp: textStream.streamInfo.timestamp,
    message: textStream.text,
    from:
      textStream.participantInfo.identity === room.localParticipant.identity
        ? room.localParticipant
        : Array.from(room.remoteParticipants.values()).find(
            (p) => p.identity === textStream.participantInfo.identity
          ),
  };
}

interface LiveTranscriptProps {
  className?: string;
}

export function LiveTranscript({ className }: LiveTranscriptProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const room = useRoomContext();
  const transcriptions: TextStreamData[] = useTranscriptions();

  // Convert transcriptions to chat messages for display
  const transcriptMessages = useMemo(() => {
    return transcriptions.map((transcription) => transcriptionToChatMessage(transcription, room));
  }, [transcriptions, room]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [transcriptMessages]);

  return (
    <div
      className={cn(
        'fixed top-0 right-0 bottom-0 z-40 w-[380px] border-l border-border/50 bg-background/95 backdrop-blur-sm flex flex-col',
        className
      )}
    >
      {/* Header */}
      <div className="border-b border-border/50 px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Transcript</h3>
      </div>

      {/* Transcript Content */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 px-4 py-4">
        {transcriptMessages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">Transcript will appear here...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {transcriptMessages.map(({ id, timestamp, from, message, editTimestamp }) => {
              const locale = navigator?.language ?? 'en-US';
              const messageOrigin = from?.isLocal ? 'local' : 'remote';
              const hasBeenEdited = !!editTimestamp;

              return (
                <ChatEntry
                  key={id}
                  locale={locale}
                  timestamp={timestamp}
                  message={message}
                  messageOrigin={messageOrigin}
                  hasBeenEdited={hasBeenEdited}
                  className="text-sm"
                />
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

