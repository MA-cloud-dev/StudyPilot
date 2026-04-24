import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

const fixturePath = path.resolve(__dirname, "fixtures", "probability-notes.md");

async function createProfile(page: Page, goal: string) {
  await page.goto("/profile");
  await page.getByLabel("学习目标").fill(goal);
  await page.getByLabel("学科范围").fill("math");
  await page.getByLabel("当前基础").selectOption("beginner");
  await page.getByLabel("时间预算").fill("45");
  await page.getByLabel("单位").selectOption("day");
  await page.getByLabel("讲解风格").selectOption("practical");
  await page.getByLabel("难度偏好").selectOption("medium");
  await page.getByRole("button", { name: "保存档案" }).click();
  await expect(page.getByText("学习者档案已保存，下一步可以生成学习计划。")).toBeVisible();
}

async function uploadKnowledge(page: Page, title: string) {
  await page.goto("/knowledge");
  await page.locator('input[type="file"]').setInputFiles(fixturePath);
  await page.getByLabel("统一标题（可选）").fill(title);
  await page.getByLabel("标签（逗号分隔，可选）").fill("probability,phase3");
  await page.getByRole("button", { name: "上传资料" }).click();

  const assetCard = page.locator("article").filter({ hasText: title });
  await expect(assetCard).toBeVisible();
  await expect(assetCard).toContainText(".md");
  await expect(assetCard).toContainText("ready");
}

async function generatePlan(page: Page, assetTitle?: string) {
  await page.goto("/plans");
  await expect(page.getByText(/创建新计划/)).toBeVisible();
  await page.getByPlaceholder("描述学习目标...").fill(
    assetTitle
      ? `我想学习概率论，并结合 ${assetTitle} 做一轮 8 周复习`
      : "我想学习概率论，希望 8 周内完成一轮复习",
  );
  await page.getByRole("button", { name: "➤" }).click();
  await page.getByRole("button", { name: "生成计划" }).click();
  await expect(page.getByText("计划已创建：")).toBeVisible();
  await expect(page.getByText(/Learning Plan/i).first()).toBeVisible();
}

async function completeLearning(page: Page, question: string) {
  await page.goto("/workbench");
  await page.getByRole("button", { name: /启动学习会话|重新开始本次学习/ }).click();
  await expect(page.getByText("当前摘要")).toBeVisible();
  await page.getByPlaceholder("例如：请用更通俗的方式解释这个主题。").fill(question);
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.getByText(question, { exact: true })).toBeVisible();
  await expect(page.getByText("Current focus:")).toBeVisible();
  await page.getByRole("button", { name: "完成学习并进入阶段测试" }).click();
  await expect(page.getByTestId("workbench-session-complete")).toBeVisible();
}

async function generateCheckpointAssessment(page: Page) {
  await page.goto("/assessments");
  const regenerateButton = page.getByRole("button", { name: /重新生成.*测试/ });
  if (await regenerateButton.isVisible().catch(() => false)) {
    await regenerateButton.click();
  }
  await expect(page.getByText("Question 1", { exact: true })).toBeVisible();
  await expect(page.getByText("Question 12", { exact: true })).toBeVisible();
  await expect(page.getByTestId("assessment-status")).toContainText("generated");
  await page.reload();
  await expect(page.getByText("Question 1", { exact: true })).toBeVisible();
}

async function submitPassingAssessment(page: Page) {
  for (let index = 1; index <= 10; index += 1) {
    const questionCard = page.locator("article").filter({ hasText: `Question ${index}` });
    await questionCard.locator('input[type="radio"]').first().check();
  }

  for (let index = 11; index <= 12; index += 1) {
    const questionCard = page.locator("article").filter({ hasText: `Question ${index}` });
    const questionStem = (await questionCard.locator("h3").textContent()) ?? "";
    const topic = extractTopic(questionStem);
    await questionCard.locator("textarea").fill(
      `${topic} supports the current study scope by clarifying the core idea and preparing the learner for the next micro study step.`,
    );
  }

  await page.getByRole("button", { name: "提交答案" }).click();
  await expect(page.getByText("通过")).toBeVisible();
  await expect(page.getByTestId("assessment-workflow-status")).toBeVisible();
}

async function submitFailingAssessment(page: Page) {
  for (let index = 1; index <= 4; index += 1) {
    const questionCard = page.locator("article").filter({ hasText: `Question ${index}` });
    await questionCard.locator('input[type="radio"]').nth(1).check();
  }

  for (let index = 5; index <= 12; index += 1) {
    const questionCard = page.locator("article").filter({ hasText: `Question ${index}` });
    await questionCard.getByLabel("我不确定这题").check();
  }

  await page.getByRole("button", { name: "提交答案" }).click();
  await expect(page.getByText("未通过")).toBeVisible();
}

function extractTopic(questionStem: string) {
  const match = questionStem.match(/role of (.+) in the current study scope/i);
  return match?.[1] ?? "the current topic";
}

test.describe.serial("checkpoint gating loop", () => {
  test("passing checkpoint unlocks the next micro study session and finishing the last one completes the cycle", async ({ page }) => {
    await createProfile(page, "Learn probability through checkpoint-gated micro sessions");
    await uploadKnowledge(page, "Probability Notes");
    await generatePlan(page, "Probability Notes");

    await completeLearning(page, "Please explain conditional probability in simple terms.");
    await generateCheckpointAssessment(page);
    await submitPassingAssessment(page);

    await expect(page.getByTestId("assessment-workflow-status")).toContainText("learning");
    await page.getByRole("button", { name: "进入下一次微观学习" }).click();
    await expect(page).toHaveURL(/\/workbench$/);

    await completeLearning(page, "Please explain the next topic in simple terms.");
    await generateCheckpointAssessment(page);
    await submitPassingAssessment(page);

    await expect(page.getByTestId("assessment-workflow-status")).toContainText("next_cycle");
    await page.getByRole("button", { name: "开启下一轮计划" }).click();
    await expect(page).toHaveURL(/\/plans$/);
  });

  test("weak checkpoint submission keeps the learner in the current micro study session with detailed feedback", async ({ page }) => {
    await createProfile(page, "Refresh probability fundamentals with checkpoint feedback");
    await generatePlan(page);
    await completeLearning(page, "Please summarize the current topic once.");
    await generateCheckpointAssessment(page);

    await submitFailingAssessment(page);

    await expect(page.getByTestId("assessment-workflow-status")).toContainText("learning");
    await expect(page.getByText("错误原因：The selected option does not match the correct answer.").first()).toBeVisible();
    await expect(page.getByText("This question was marked as uncertain, so it received 0 points.").first()).toBeVisible();
    await page.getByRole("button", { name: "返回当前微观学习" }).click();
    await expect(page).toHaveURL(/\/workbench$/);
  });
});
