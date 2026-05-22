import { Component, CUSTOM_ELEMENTS_SCHEMA, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarkdownModule } from 'ngx-markdown';
import 'mathlive'; // โหลด MathLive

// 1. นำ Mock Data มาวางไว้นอก Class (หรือประกาศเป็น class property แทน)
const MOCK_DATA = `การหาค่าลิมิตของฟังก์ชันนี้ สามารถใช้วิธี **L'Hôpital's Rule** (กฎของโลปีตาล) เนื่องจากเมื่อแทนค่า $x = 0$ จะได้รูปแบบไม่กำหนด $\\frac{0}{0}$



**ขั้นตอนที่ 1:** หาอนุพันธ์ของเศษและส่วน \\
จาก $$\\lim_{x \\to 0} \\frac{\\sin(x)}{x}$$


หาอนุพันธ์ของตัวเศษ:
$$ \\frac{d}{dx}[\\sin(x)] = \\cos(x) $$

หาอนุพันธ์ของตัวส่วน:
$$ \\frac{d}{dx}[x] = 1 $$

**ขั้นตอนที่ 2:** นำมาแทนค่าในลิมิต
$$ \\lim_{x \\to 0} \\frac{\\cos(x)}{1} = \\frac{\\cos(0)}{1} = 1 $$

**สรุปคำตอบ:** ค่าของลิมิตคือ **1**`;

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [CommonModule, FormsModule, MarkdownModule],
  schemas: [CUSTOM_ELEMENTS_SCHEMA], // จำเป็นสำหรับ <math-field>
  templateUrl: './chat-page.html',
  styleUrl: './chat-page.scss',
})
export class ChatPage {
  private _sseBuffer = '';

  question = signal(''); // ใส่โจทย์จำลองไว้ในช่องพิมพ์ \\lim_{x \\to 0} \\frac{\\sin(x)}{x}
  wolframRaw = signal(''); // ใส่ค่าจำลองให้ Wolfram limit of sin(x)/x as x->0

  // 2. ใส่ MOCK_DATA เป็นค่าเริ่มต้นให้ทั้ง 3 กล่อง
  responses = signal({
    llama: '',
    gemini: '',
    qwen: '',
  });

  isStreaming = signal(false);
  // 3. ปรับเป็น true เพื่อให้ UI โชว์ผลลัพธ์ทันทีที่เปิดหน้าเว็บ
  hasResult = signal(false);
  currentResponseId = signal<number | null>(null);

  currentSlide = signal(0);

  readonly slideKeys = ['llama', 'gemini', 'qwen'] as const;
  readonly slideLabels = ['Llama', 'Gemini', 'Qwen'];

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
    this.wolframRaw.set('');
    this.responses.set({ llama: '', gemini: '', qwen: '' });
    this._sseBuffer = '';

    try {
      const response = await fetch('http://127.0.0.1:8000/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: this.question() }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');

      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        this.parseSSEChunk(chunk);
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
          } else if (data.type === 'chunk') {
            this.responses.update((current) => ({
              ...current,
              [data.model]: current[data.model as keyof typeof current] + data.content,
            }));
          }
        } catch (e) {
          // ข้าม chunk ที่ parse ไม่ได้
        }
      }
    }
  }

  private _flushSSEBuffer() {
    // SSE events คั่นด้วย \n\n
    const parts = this._sseBuffer.split('\n\n');
    // ส่วนสุดท้ายอาจยังไม่สมบูรณ์ → เก็บไว้รอ
    this._sseBuffer = parts.pop() ?? '';

    for (const part of parts) {
      for (const line of part.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'wolfram') {
              this.wolframRaw.set(data.content);
            } else if (data.type === 'chunk') {
              this.responses.update((cur) => ({
                ...cur,
                [data.model]: cur[data.model as keyof typeof cur] + data.content,
              }));
            }
          } catch {}
        }
      }
    }
  }

  async vote(modelName: string) {
    alert(`โหวตเรียบร้อยแล้ว!`);
  }
}
