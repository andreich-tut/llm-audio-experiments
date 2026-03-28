# Prompt: Advanced JavaScript Code Churn & Diff Analyzer (V2)

**Role:** You are a Senior Software Engineer specializing in VCS (Version Control Systems) and string-processing algorithms.

**Task:** Write a robust, production-ready JavaScript function `calculateCodeChurn(oldCode, newCode, options)` that performs a line-by-line diff to calculate **Added**, **Removed**, and **Modified** counts.

---

### 1. Algorithm & Logic Requirements
* **Diff Engine:** Use a **Myers Diff Algorithm** or **Longest Common Subsequence (LCS)** approach. Do **NOT** use simple index-to-index comparison, as any line insertion must not offset the rest of the file.
* **Defining "Modified":** A line is "Modified" if a deletion and an addition occur at the same logical position. 
    * **Look-ahead Window:** When a line is removed, the algorithm should look ahead up to **3 lines** in the "Added" set to find a potential match.
    * **Similarity Logic:** A pair of lines is "Modified" if their Levenshtein Distance similarity is **> 50%**. 
* **No Double-Counting:** A modified line counts as **1** modification. It must **not** be counted as 1 addition and 1 removal.

### 2. Mathematical Specifications
* **Total Lines:** `totalLinesNew` is the count of lines in the `newCode` string after normalization.
* **Change Percentage:** Calculate this based on the original file size to represent "churn" relative to the starting point. Use the following formula:
  
  $$\text{changePercentage} = \min\left(100, \left( \frac{\text{added} + \text{removed} + \text{modified}}{\max(1, \text{totalLinesOld})} \right) \times 100\right)$$

  *(Note: Cap the display at 100.0% for reporting purposes, formatted as a string with one decimal place).*

### 3. Engineering Constraints & Edge Cases
* **Performance Safety:** If either input exceeds **5,000 lines**, the function should throw a custom error or switch to a basic hunk-based comparison to prevent blocking the event loop ($O(N^2)$ protection).
* **Normalization:** * Handle `\r\n` and `\n` interchangeably.
    * If `options.ignoreWhitespace` is true, trim leading/trailing whitespace before comparison.
* **Null Safety:** If `oldCode` is null/empty and `newCode` has 10 lines, the result should be `added: 10, removed: 0, modified: 0`.
* **Identity Check:** Perform an initial `===` check; if strings are identical, return all zeros immediately.

### 4. Function Signature
```javascript
/**
 * @param {string} oldCode - The original source code
 * @param {string} newCode - The updated source code
 * @param {Object} [options] 
 * @param {boolean} [options.ignoreWhitespace=true]
 * @param {number} [options.similarityThreshold=0.5]
 */
function calculateCodeChurn(oldCode, newCode, options = {}) { 
    // Implementation here
}
* **Identity Check:** Perform an initial `===` check; if strings are identical, return all zeros immediately.

### 4. Expected Output Format
Return a plain JavaScript object:
```
{
  "added": 12,
  "removed": 4,
  "modified": 3,
  "totalLinesNew": 125,
  "changePercentage": "15.2%"
}
```