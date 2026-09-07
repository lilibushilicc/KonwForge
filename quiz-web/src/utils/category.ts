import type { Category } from "../api/categories";

export interface TreeNode {
  title: string;
  value: number;
  children: TreeNode[];
}

/** 扁平分类列表 → Ant Design TreeSelect/Tree 的 treeData 结构。 */
export function buildCategoryTree(list: Category[]): TreeNode[] {
  const map = new Map<number, TreeNode>();
  list.forEach((c) => map.set(c.id, { title: c.name, value: c.id, children: [] }));

  const roots: TreeNode[] = [];
  list.forEach((c) => {
    const node = map.get(c.id)!;
    if (c.parent_id != null && map.has(c.parent_id)) {
      map.get(c.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  });
  return roots;
}

/** 找到某 id 的全部子孙 id（含自身），用于「含子分类」筛选提示。 */
export function descendantIds(list: Category[], rootId: number): number[] {
  const childrenOf = new Map<number, number[]>();
  list.forEach((c) => {
    if (c.parent_id != null) {
      const arr = childrenOf.get(c.parent_id) ?? [];
      arr.push(c.id);
      childrenOf.set(c.parent_id, arr);
    }
  });
  const out: number[] = [rootId];
  const stack = [rootId];
  while (stack.length) {
    const cur = stack.pop()!;
    for (const child of childrenOf.get(cur) ?? []) {
      out.push(child);
      stack.push(child);
    }
  }
  return out;
}
