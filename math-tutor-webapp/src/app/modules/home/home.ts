import {
  ChangeDetectorRef,
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  inject,
  OnInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { SelectButtonModule } from 'primeng/selectbutton';
import { ProgressBarModule } from 'primeng/progressbar';
import 'mathlive';
import { MathFieldAccessor } from './math-field.accessor';
import { MathTutorService } from '../../shared/services/math-tutor';

// ── Preview helper ─────────────────────────────────────────────
export interface LatexSegment {
  type: 'text' | 'math';
  value: string;
}

export function splitLatexAndText(latex: string): LatexSegment[] {
  if (!latex?.trim()) return [];

  const segments: LatexSegment[] = [];
  let remaining = latex;

  while (remaining.length > 0) {
    const idx = remaining.indexOf('\\text{');
    if (idx === -1) {
      const math = remaining.trim();
      if (math) segments.push({ type: 'math', value: math });
      break;
    }

    const before = remaining.slice(0, idx).trim();
    if (before) segments.push({ type: 'math', value: before });

    // อ่าน content ใน \text{...} รองรับ nested braces
    let depth = 0,
      i = idx + 6,
      content = '';
    for (; i < remaining.length; i++) {
      if (remaining[i] === '{') depth++;
      else if (remaining[i] === '}') {
        if (depth === 0) {
          i++;
          break;
        }
        depth--;
      }
      content += remaining[i];
    }
    if (content.trim()) segments.push({ type: 'text', value: content });
    remaining = remaining.slice(i);
  }

  return segments;
}

// ──────────────────────────────────────────────────────────────

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    SelectButtonModule,
    ProgressBarModule,
    MathFieldAccessor, // ← import accessor directive
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class Home implements OnInit {
  private readonly _mathTutorService = inject(MathTutorService);
  private readonly _cdr: ChangeDetectorRef = inject(ChangeDetectorRef);

  ngOnInit(): void {
    this;
  }

  // ── Model Selection ──────────────────────────
  modelOptions = [
    { label: 'Model 1', value: '1', desc: 'Llama' },
    { label: 'Model 2', value: '2', desc: 'Deepseek' },
    { label: 'Model 3', value: '3', desc: 'Gemini' },
  ];
  selectedModel = '1';

  // ── State ────────────────────────────────────
  // latexValue เป็น single source of truth
  // ทั้ง [(ngModel)] และ preview อ่านจากตัวเดียวกัน
  latexValue = '';

  isProcessing = false;
  showResults = false;

  // ── Mock Data ────────────────────────────────
  wolframResult = {
    answer: 'x = \\pm 2i',
    steps: ['จัดรูปสมการใหม่', 'ย้ายข้างค่าคงที่', 'ถอดรากที่สองของจำนวนลบ'],
  };

  chatMessages: string = '';
  isTyping = false;

  examples = [
    { label: 'Integral', latex: '\\int_0^\\pi \\sin(x)\\,dx' },
    {
      label: 'Limit',
      latex: '\\text{ให้ } f(x)=\\frac{|x|}{x} \\text{ จงหาลิมิตเมื่อ } x\\to 0',
    },
    { label: 'Matrix', latex: '\\begin{pmatrix}1&2\\\\3&4\\end{pmatrix}' },
    { label: 'Equation', latex: 'x^2+4=0' },
  ];

  // ── Preview (computed getter) ─────────────────
  get previewHtml(): string {
    return this.buildPreviewHtml(this.latexValue);
  }

  buildPreviewHtml(latex: string): string {
    if (!latex?.trim()) return '';

    const katex = (window as any)['katex'];
    if (!katex) return '<span class="preview-loading">กำลังโหลด KaTeX…</span>';

    return splitLatexAndText(latex)
      .map((seg) => {
        if (seg.type === 'text') {
          return `<span class="preview-thai">${this.escapeHtml(seg.value)}</span>`;
        }
        try {
          return `<span class="preview-math">${katex.renderToString(seg.value, {
            throwOnError: false,
            displayMode: false,
            strict: 'ignore',
          })}</span>`;
        } catch {
          return `<span class="preview-error">⚠ ${this.escapeHtml(seg.value)}</span>`;
        }
      })
      .join(' ');
  }

  private escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ── Actions ───────────────────────────────────
  loadExample(latex: string): void {
    this.latexValue = latex; // ngModel จะ writeValue ให้อัตโนมัติ
  }

  async submitQuestion(): Promise<void> {
    if (!this.latexValue.trim()) return;

    this.isProcessing = true;
    this.showResults = false;
    this.chatMessages = '';

    await new Promise((r) => setTimeout(r, 1500));

    this.isProcessing = false;
    this.showResults = true;
    this.simulateChat();
  }

  async simulateChat(): Promise<void> {
    this.isTyping = true;
    const responses = [
      'สวัสดีครับ! ผมได้รับโจทย์แคลคูลัสของคุณแล้ว',
      `จากการวิเคราะห์ด้วย Model ${this.selectedModel} และ Wolfram…`,
      'คำตอบหลักคือ $x = \\pm 2i$ ซึ่งเป็นจำนวนเชิงซ้อนครับ',
    ];
    for (const msg of responses) {
      await new Promise((r) => setTimeout(r, 1000));
      this.chatMessages += msg + ' ';
    }
    this.isTyping = false;
  }

  clearMath(): void {
    this.latexValue = ''; // ngModel clear math-field อัตโนมัติ
    this.showResults = false;
  }

  subMitQuestion(): void {
    console.log('Submitting question:', this.latexValue, 'with model', this.selectedModel);
    this.chatMessages = 'กำลังส่งคำถามไปยัง API...';
    this._mathTutorService
      .askQuestion('session123', this.latexValue, this.selectedModel)
      .subscribe({
        next: (res) => {
          console.log('API Response:', res);
          this.chatMessages = 'นี่คือคำตอบจาก API: ' + res.explanation;
          this._cdr.markForCheck();
        },
      });
  }
}
