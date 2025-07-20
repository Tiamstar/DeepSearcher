import { AnimatorOptions, AnimatorResult } from '@kit.ArkUI';

/**
 * 日期：2025/6/7
 */
export const FULL_PERCENT = "100%"

export const ANIMATE_TIME = 300

export const IMAGE_PREVIEW_SWIPER_CONTROLLER = "imagePreviewSwiperConfig"

type ImageAction = Callback<number>
type AnimType = 'scale' | 'offsetX' | 'offsetY'

export class ImageAnimUtil {
  private readonly uiContext: UIContext
  private readonly animMap: Map<AnimType, AnimatorResult> = new Map()

  constructor(uiContext: UIContext) {
    this.uiContext = uiContext;
  }

  playScale(begin: number, end: number, action: ImageAction) {
    this.play('scale', this.getOptions(begin, end), action)
  }

  playOffsetX(begin: number, end: number, action: ImageAction) {
    this.play('offsetX', this.getOptions(begin, end, 500), action)
  }

  playOffsetY(begin: number, end: number, action: ImageAction) {
    this.play('offsetY', this.getOptions(begin, end, 500), action)
  }

  stop() {
    for (let anim of this.animMap.values()) {
      anim.pause()
    }
  }

  private play(type: AnimType, option: AnimatorOptions, action: ImageAction) {
    this.animMap.get(type)?.pause()
    if (option.begin === option.end) {
      return
    }
    const anim = this.uiContext.createAnimator(option)
    anim.onFrame = action
    this.animMap.set(type, anim)
    anim.play()
  }

  private getOptions(begin: number, end: number, duration: number = 300) {
    return {
      duration,
      easing: "ease-out",
      delay: 0,
      fill: "forwards",
      direction: "normal",
      iterations: 1,
      begin,
      end
    } as AnimatorOptions
  }
}
