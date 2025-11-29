using TMPro;
using UnityEngine;
using MixedReality.Toolkit.UX.Experimental;

namespace MixedReality.Toolkit.Examples.Demos
{
    /// <summary>
    /// A more stateful demo for virtualized scroll lists:
    /// - tracks its own sine wave phase
    /// - exposes page-based navigation
    /// - labels items with index and a word
    /// </summary>
    [AddComponentMenu("MRTK/Examples/Virtualized Scroll Rect Sine Controller")]
    public class VirtualizedScrollRectSineController : MonoBehaviour
    {
        [SerializeField]
        private bool playSineAnimation = true;

        [SerializeField]
        private float phaseSpeed = 0.5f;

        [SerializeField]
        private float snapThreshold = 0.02f;

        [SerializeField]
        private float jumpLerpSpeed = 8f;

        private VirtualizedScrollRectList list;
        private float currentPhase;
        private float targetScroll;
        private bool isJumping;

        private readonly string[] words = { "one", "two", "three", "zebra", "keyboard", "rabbit", "graphite", "ruby" };

        private void OnEnable()
        {
            list = GetComponent<VirtualizedScrollRectList>();
            list.OnVisible = PopulateRow;
        }

        private void PopulateRow(GameObject row, int index)
        {
            var label = row.GetComponentInChildren<TextMeshProUGUI>();
            if (label != null)
            {
                label.text = $"{index} {words[index % words.Length]}";
            }
        }

        private void Update()
        {
            if (playSineAnimation)
            {
                currentPhase += phaseSpeed * Time.deltaTime;
                float normalized = Mathf.InverseLerp(-1f, 1f, Mathf.Sin(currentPhase));
                list.Scroll = normalized * list.MaxScroll;

                isJumping = false;
                targetScroll = list.Scroll;
            }
            else if (isJumping)
            {
                list.Scroll = Mathf.Lerp(list.Scroll, targetScroll, jumpLerpSpeed * Time.deltaTime);
                if (Mathf.Abs(list.Scroll - targetScroll) < snapThreshold)
                {
                    list.Scroll = targetScroll;
                    isJumping = false;
                }
            }
        }

        public void GoToNextPage()
        {
            playSineAnimation = false;
            isJumping = true;

            float pageSize = list.TotallyVisibleCount;
            float currentPageStart = Mathf.Floor(list.Scroll / pageSize) * pageSize;
            targetScroll = Mathf.Clamp(currentPageStart + pageSize, 0, list.MaxScroll);
        }

        public void GoToPreviousPage()
        {
            playSineAnimation = false;
            isJumping = true;

            float pageSize = list.TotallyVisibleCount;
            float currentPageStart = Mathf.Floor(list.Scroll / pageSize) * pageSize;
            targetScroll = Mathf.Clamp(currentPageStart - pageSize, 0, list.MaxScroll);
        }

        [ContextMenu("50 Items")]
        public void SetFiftyItems() => list.SetItemCount(50);

        [ContextMenu("200 Items")]
        public void SetTwoHundredItems() => list.SetItemCount(200);
    }
}
