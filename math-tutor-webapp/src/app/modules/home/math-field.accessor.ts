import { Directive, ElementRef, forwardRef, HostListener, OnDestroy, OnInit } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

/**
 * MathFieldAccessor
 * ─────────────────
 * ทำให้ <math-field> ใช้งาน [(ngModel)] ได้เหมือน input ปกติ
 *
 * Usage ใน template:
 *   <math-field mathFieldAccessor [(ngModel)]="latexValue"></math-field>
 */
@Directive({
  selector: 'math-field[mathFieldAccessor]',
  standalone: true,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MathFieldAccessor),
      multi: true,
    },
  ],
})
export class MathFieldAccessor implements ControlValueAccessor, OnInit, OnDestroy {
  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  // เก็บ listener ref เพื่อ removeEventListener ตอน destroy
  private inputHandler = (e: Event) => {
    const val = (e.target as any).value ?? '';
    this.onChange(val);
  };

  private blurHandler = () => {
    this.onTouched();
  };

  constructor(private el: ElementRef<any>) {}

  ngOnInit(): void {
    const mf = this.el.nativeElement;

    // MathLive options — ตั้งที่นี่เลยไม่ต้องไป ngAfterViewInit ใน component
    mf.setOptions?.({
      smartMode: true, // auto-detect Thai text vs math
      smartFence: true,
      removeExtraneousParentheses: true,
    });

    mf.addEventListener('input', this.inputHandler);
    mf.addEventListener('blur', this.blurHandler);
  }

  ngOnDestroy(): void {
    const mf = this.el.nativeElement;
    mf.removeEventListener('input', this.inputHandler);
    mf.removeEventListener('blur', this.blurHandler);
  }

  // ── ControlValueAccessor ──────────────────────

  /** Angular → DOM: set ค่าเข้า math-field */
  writeValue(value: string): void {
    const mf = this.el.nativeElement;
    // ป้องกัน loop: เขียนเฉพาะเมื่อค่าต่างจากที่แสดงอยู่
    if (mf.value !== (value ?? '')) {
      mf.value = value ?? '';
    }
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  /** Angular Forms: set disabled state */
  setDisabledState(isDisabled: boolean): void {
    this.el.nativeElement.disabled = isDisabled;
  }
}
