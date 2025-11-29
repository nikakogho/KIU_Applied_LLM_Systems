using TMPro;
using UnityEngine;
using MixedReality.Toolkit.UX.Experimental;

namespace MixedReality.Toolkit.Examples.Demos
{
    [AddComponentMenu("MRTK/Examples/Virtualized Scroll Rect List Tester")]
    public class VirtualizedScrollRectListTester : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("If true, the list will be driven by a sine-based auto scroll.")]
        private bool useSinusScroll = true;

        private VirtualizedScrollRectList list;
        private float targetScroll;
        private bool shouldAnimate;

        private readonly string[] labelWords = { "one", "two", "three", "zebra", "keyboard", "rabbit", "graphite", "ruby" };

        private void Start()
        {
            list = GetComponent<VirtualizedScrollRectList>();
            list.OnVisible = UpdateVisibleItem;
        }

        private void Update()
        {
            if (useSinusScroll)
            {
                ApplySinusoidalScroll();
            }

            if (shouldAnimate)
            {
                AnimateTowardsTarget();
            }
        }

        private void UpdateVisibleItem(GameObject go, int index)
        {
            foreach (var text in go.GetComponentsInChildren<TextMeshProUGUI>())
            {
                if (text.gameObject.name == "Text")
                {
                    text.text = $"{index} {labelWords[index % labelWords.Length]}";
                }
            }
        }

        private void ApplySinusoidalScroll()
        {
            float angle = Time.time * 0.5f - Mathf.PI / 2f;
            float normalized = Mathf.Sin(angle) * 0.5f + 0.5f;
            list.Scroll = normalized * list.MaxScroll;

            targetScroll = list.Scroll;
            shouldAnimate = false;
        }

        private void AnimateTowardsTarget()
        {
            list.Scroll = Mathf.Lerp(list.Scroll, targetScroll, 8f * Time.deltaTime);
            if (Mathf.Abs(list.Scroll - targetScroll) < 0.02f)
            {
                list.Scroll = targetScroll;
                shouldAnimate = false;
            }
        }

        public void Next()
        {
            useSinusScroll = false;
            shouldAnimate = true;

            float pageBase = Mathf.Floor(list.Scroll / list.RowsOrColumns) * list.RowsOrColumns;
            targetScroll = Mathf.Min(list.MaxScroll, pageBase + list.TotallyVisibleCount);
        }

        public void Prev()
        {
            useSinusScroll = false;
            shouldAnimate = true;

            float pageBase = Mathf.Floor(list.Scroll / list.RowsOrColumns) * list.RowsOrColumns;
            targetScroll = Mathf.Max(0f, pageBase - list.TotallyVisibleCount);
        }

        [ContextMenu("Set Item Count 50")]
        public void SetCount50() => list.SetItemCount(50);

        [ContextMenu("Set Item Count 200")]
        public void SetCount200() => list.SetItemCount(200);
    }
}
