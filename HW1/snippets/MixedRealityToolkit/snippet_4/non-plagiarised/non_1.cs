using TMPro;
using UnityEngine;
using MixedReality.Toolkit.UX.Experimental;

namespace MixedReality.Toolkit.Examples.Demos
{
    /// <summary>
    /// Controls a virtualized list by assigning labels, auto-scrolling with a sine wave,
    /// and exposing page-based navigation commands.
    /// </summary>
    [AddComponentMenu("MRTK/Examples/Virtualized Scroll Rect Pager")]
    public class VirtualizedScrollRectPager : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("If true, the list will endlessly scroll in a sine pattern.")]
        private bool autoPlay = true;

        [SerializeField]
        [Tooltip("Speed multiplier for the sine wave scroll.")]
        private float autoSpeed = 0.5f;

        [SerializeField]
        [Tooltip("How quickly we interpolate when jumping between pages.")]
        private float pageLerpSpeed = 8f;

        private VirtualizedScrollRectList list;
        private float targetScroll;
        private bool jumpingToPage;
        private int currentPageIndex;

        private readonly string[] labelWords = { "one", "two", "three", "zebra", "keyboard", "rabbit", "graphite", "ruby" };

        private void Awake()
        {
            list = GetComponent<VirtualizedScrollRectList>();

            // Label each visible row with its index and a word.
            list.OnVisible = (go, index) =>
            {
                var text = go.GetComponentInChildren<TextMeshProUGUI>();
                if (text != null)
                {
                    string word = labelWords[index % labelWords.Length];
                    text.text = $"{index} {word}";
                }
            };
        }

        private void Update()
        {
            if (autoPlay)
            {
                float normalized = 0.5f * (Mathf.Sin(Time.time * autoSpeed) + 1f);
                list.Scroll = normalized * list.MaxScroll;
                jumpingToPage = false;
                targetScroll = list.Scroll;
            }
            else if (jumpingToPage)
            {
                list.Scroll = Mathf.Lerp(list.Scroll, targetScroll, pageLerpSpeed * Time.deltaTime);
                if (Mathf.Abs(list.Scroll - targetScroll) <= 0.02f)
                {
                    list.Scroll = targetScroll;
                    jumpingToPage = false;
                }
            }
        }

        public void NextPage()
        {
            autoPlay = false;

            int pageSize = list.TotallyVisibleCount;
            int totalPages = Mathf.Max(1, Mathf.CeilToInt(list.MaxScroll / pageSize));

            currentPageIndex = Mathf.Clamp(currentPageIndex + 1, 0, totalPages - 1);
            targetScroll = Mathf.Clamp(currentPageIndex * pageSize, 0f, list.MaxScroll);
            jumpingToPage = true;
        }

        public void PreviousPage()
        {
            autoPlay = false;

            int pageSize = list.TotallyVisibleCount;
            int totalPages = Mathf.Max(1, Mathf.CeilToInt(list.MaxScroll / pageSize));

            currentPageIndex = Mathf.Clamp(currentPageIndex - 1, 0, totalPages - 1);
            targetScroll = Mathf.Clamp(currentPageIndex * pageSize, 0f, list.MaxScroll);
            jumpingToPage = true;
        }

        [ContextMenu("Set Item Count 50")]
        public void UseFiftyItems() => list.SetItemCount(50);

        [ContextMenu("Set Item Count 200")]
        public void UseTwoHundredItems() => list.SetItemCount(200);
    }
}
