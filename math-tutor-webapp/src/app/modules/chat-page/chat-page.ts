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
  question = signal('\\lim_{x \\to 0} \\frac{\\sin(x)}{x}'); // ใส่โจทย์จำลองไว้ในช่องพิมพ์
  wolframRaw = signal('limit of sin(x)/x as x->0'); // ใส่ค่าจำลองให้ Wolfram

  // 2. ใส่ MOCK_DATA เป็นค่าเริ่มต้นให้ทั้ง 3 กล่อง
  responses = signal({
    llama: MOCK_DATA,
    deepseek: MOCK_DATA,
    qwen: MOCK_DATA,
  });

  isStreaming = signal(false);
  // 3. ปรับเป็น true เพื่อให้ UI โชว์ผลลัพธ์ทันทีที่เปิดหน้าเว็บ
  hasResult = signal(true);
  currentResponseId = signal<number | null>(null);

  async askQuestion() {
    if (!this.question()) return;

    this.isStreaming.set(true);
    this.hasResult.set(true);
    this.wolframRaw.set('');
    this.responses.set({ llama: '', deepseek: '', qwen: '' });

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

  async vote(modelName: string) {
    alert(`โหวตให้โมเดล: ${modelName} เรียบร้อยแล้ว!`);
  }
}
