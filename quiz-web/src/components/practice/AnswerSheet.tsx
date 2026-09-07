import { Tooltip, Typography } from "antd";

export type SheetState = "unanswered" | "answered" | "correct" | "incorrect";

export interface SheetCell {
  index: number; // 0-based
  state: SheetState;
  flagged: boolean;
}

/**
 * 答题卡：网格展示每题作答状态，支持点击跳转到指定题、标记题目。
 * - 交卷前：已答 / 未答（未答高亮，便于「标记未答题目」）
 * - 交卷后：正确 / 错误
 */
export function AnswerSheet({
  cells,
  submitted,
  onJump,
  onToggleFlag,
}: {
  cells: SheetCell[];
  submitted: boolean;
  onJump: (index: number) => void;
  onToggleFlag?: (index: number) => void;
}) {
  const unanswered = cells.filter((c) => c.state === "unanswered").length;
  const flaggedCount = cells.filter((c) => c.flagged).length;

  return (
    <div className="answer-sheet">
      <div className="answer-sheet__head">
        <Typography.Text strong>答题卡</Typography.Text>
        {!submitted ? (
          <Typography.Text type="danger" style={{ fontSize: 12 }}>
            未答 {unanswered} 题
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            共 {cells.length} 题
          </Typography.Text>
        )}
      </div>

      <div className="answer-sheet__grid">
        {cells.map((c) => {
          const cls =
            c.state === "correct"
              ? "is-correct"
              : c.state === "incorrect"
              ? "is-incorrect"
              : c.state === "answered"
              ? "is-answered"
              : "is-unanswered";
          return (
            <Tooltip key={c.index} title={c.flagged ? "已标记，点击星标取消" : "点击跳转到此题"}>
              <button
                type="button"
                className={`sheet-cell ${cls}`}
                onClick={() => onJump(c.index)}
              >
                {c.index + 1}
                {c.flagged && (
                  <span
                    className="sheet-cell__flag"
                    role="button"
                    aria-label="切换标记"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleFlag?.(c.index);
                    }}
                  >
                    ★
                  </span>
                )}
              </button>
            </Tooltip>
          );
        })}
      </div>

      <div className="answer-sheet__legend">
        <span>
          <i className="dot is-answered" />
          {submitted ? "已答" : "已答"}
        </span>
        <span>
          <i className="dot is-unanswered" />
          未答
        </span>
        {submitted && (
          <>
            <span>
              <i className="dot is-correct" />
              正确
            </span>
            <span>
              <i className="dot is-incorrect" />
              错误
            </span>
          </>
        )}
        {flaggedCount > 0 && (
          <span>
            <i className="dot is-flag" />
            标记 {flaggedCount}
          </span>
        )}
      </div>
    </div>
  );
}
