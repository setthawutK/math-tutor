import { Component, CUSTOM_ELEMENTS_SCHEMA, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarkdownModule } from 'ngx-markdown';
import 'mathlive';

import { KatexOptions } from 'ngx-markdown';

const NOT_MATH_MSG = `**กรุณาป้อนโจทย์คณิตศาสตร์** เช่น $$\\int x^2\\,dx$$ หรือ $$\\lim_{x \\to 0} \\frac{\\sin(x)}{x}$$`;

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [CommonModule, FormsModule, MarkdownModule],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './chat-page.html',
  styleUrl: './chat-page.scss',
})
export class ChatPage {
  question = signal('');
  wolframRaw = signal('');

  responses = signal({
    llama: '',
    openai: '',
    qwen: '',
  });

  isStreaming = signal(false);
  hasResult = signal(false);
  hasVoted = signal(false);
  currentResponseId = signal<string | null>(null);
  currentSlide = signal(0);

  readonly slideKeys = ['llama', 'openai', 'qwen'] as const;
  readonly slideLabels = ['Llama', 'DeepSeek', 'Qwen'];

  katexOpts: KatexOptions = {
    throwOnError: false,
    errorColor: '#cc0000',
  };

  slideLabel() {
    return this.slideLabels[this.currentSlide()];
  }

  currentResponse() {
    const key = this.slideKeys[this.currentSlide()];
    return this.responses()[key];
  }

  nextSlide() {
    if (this.currentSlide() < 2) this.currentSlide.update((v) => v + 1);
  }

  prevSlide() {
    if (this.currentSlide() > 0) this.currentSlide.update((v) => v - 1);
  }

  async askQuestion() {
    if (!this.question()) return;
    this.currentSlide.set(0);
    this.isStreaming.set(true);
    this.hasResult.set(true);
    this.hasVoted.set(false);
    this.wolframRaw.set('');
    this.responses.set({ llama: '', openai: '', qwen: '' });

    try {
      const response = await fetch(
        'https://math-tutor-backend-1047981882824.asia-southeast1.run.app/ask/stream',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: this.question() }),
        },
      );

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');
      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        this.parseSSEChunk(decoder.decode(value, { stream: true }));
      }
    } catch (error) {
      console.error('Error fetching stream:', error);
    } finally {
      this.isStreaming.set(false);
    }
  }

  private parseSSEChunk(chunkString: string) {
    const lines = chunkString.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.substring(6));

          if (data.type === 'wolfram') {
            this.wolframRaw.set(data.content);
          } else if (data.type === 'response_id') {
            this.currentResponseId.set(data.content);
          } else if (data.type === 'chunk') {
            this.responses.update((current) => ({
              ...current,
              [data.model]: current[data.model as keyof typeof current] + data.content,
            }));
          } else if (data.type === 'error' && data.content === 'not_math') {
            this.responses.set({
              llama: NOT_MATH_MSG,
              openai: NOT_MATH_MSG,
              qwen: NOT_MATH_MSG,
            });

            this.isStreaming.set(false);
          }
        } catch (e) {}
      }
    }
  }

  async vote(modelName: string) {
    const responseId = this.currentResponseId();
    if (!responseId || this.hasVoted()) return;

    try {
      await fetch('https://math-tutor-backend-1047981882824.asia-southeast1.run.app/vote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          response_id: responseId,
          voted_model: modelName.toLowerCase(),
        }),
      });
      this.hasVoted.set(true);
    } catch (error) {
      console.error('Vote error:', error);
    }
  }
}
