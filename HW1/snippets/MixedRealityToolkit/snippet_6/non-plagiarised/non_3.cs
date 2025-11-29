using MixedReality.Toolkit.SpatialManipulation;
using MixedReality.Toolkit.UX;
using System.Collections;
using System.Text;
using TMPro;
using UnityEngine;

namespace MixedReality.Toolkit.Examples.Demos
{
    public class BoundsControlTwoPhaseDemo : MonoBehaviour
    {
        [SerializeField]
        private TextMeshPro statusText;

        [SerializeField]
        private Material cubeMaterial;

        [SerializeField]
        private GameObject boundsVisualsPrefab;

        [SerializeField]
        private Transform cubeParent;

        private bool advance;
        private readonly Vector3 basePosition = new Vector3(0, 1.2f, 2);
        private readonly Vector3 baseSize = new Vector3(0.5f, 0.5f, 0.5f);
        private readonly StringBuilder builder = new StringBuilder();

        private void Start()
        {
            StartCoroutine(MainLoop());
        }

        private IEnumerator MainLoop()
        {
            while (true)
            {
                yield return SingleCubeDemo();
                yield return MultiRootDemo();
            }
        }

        private void SetStatus(string text)
        {
            builder.Clear();
            builder.AppendLine(text);
            builder.AppendLine("Press Next or say 'next' to continue.");
            statusText.text = builder.ToString();
        }

        private IEnumerator WaitForAdvance()
        {
            while (!advance)
            {
                yield return null;
            }

            advance = false;
        }

        private IEnumerator SingleCubeDemo()
        {
            GameObject cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.GetComponent<MeshRenderer>().material = cubeMaterial;
            cube.transform.position = basePosition;
            cube.transform.localScale = baseSize;
            cube.transform.SetParent(cubeParent == null ? transform : cubeParent);

            BoundsControl bounds = SetupBoundsControl(cube);

            SetStatus("Instantiate BoundsControl");
            yield return WaitForAdvance();

            GameObject overrideRoot = new GameObject("OverrideBounds");
            overrideRoot.transform.position = new Vector3(0.8f, 0.8f, 1.8f);
            BoxCollider overrideCollider = overrideRoot.AddComponent<BoxCollider>();
            overrideCollider.size = new Vector3(0.162f, 0.1f, 1f);
            bounds.OverrideBounds = true;
            bounds.BoundsOverride = overrideCollider.transform;

            SetStatus("Set Target bounds override");
            yield return WaitForAdvance();

            overrideCollider.size = new Vector3(0.5f, 0.1f, 1f);
            bounds.RecomputeBounds();

            SetStatus("Change target bounds override size");
            yield return WaitForAdvance();

            bounds.RotateAnchor = RotateAnchorType.ObjectOrigin;
            SetStatus("RotateAnchor Object Origin");
            yield return WaitForAdvance();

            bounds.RotateAnchor = RotateAnchorType.BoundsCenter;
            SetStatus("RotateAnchor Bounds Center");
            yield return WaitForAdvance();

            bounds.ScaleAnchor = ScaleAnchorType.OppositeCorner;
            SetStatus("ScaleAnchor Opposite Corner");
            yield return WaitForAdvance();

            bounds.ScaleAnchor = ScaleAnchorType.BoundsCenter;
            SetStatus("ScaleAnchor Bounds Center");
            yield return WaitForAdvance();

            bounds.OverrideBounds = false;
            bounds.BoundsOverride = null;
            Destroy(overrideRoot);

            SetStatus("Remove target bounds override");
            yield return WaitForAdvance();

            bounds.FlattenMode = FlattenMode.Auto;
            SetStatus("FlattenAuto");
            yield return WaitForAdvance();

            bounds.FlattenMode = FlattenMode.Always;
            SetStatus("FlattenAlways");
            yield return WaitForAdvance();

            bounds.FlattenMode = FlattenMode.Never;
            SetStatus("FlattenNever");
            yield return WaitForAdvance();

            bounds.BoundsPadding = 0.2f;
            SetStatus("BoxPadding 0.2f");
            yield return WaitForAdvance();

            bounds.BoundsPadding = 0f;
            SetStatus("BoxPadding 0");
            yield return WaitForAdvance();

            cube.transform.localScale = new Vector3(1f, 0.5f, 0.5f);
            SetStatus("Scale X and update rig");
            yield return WaitForAdvance();

            cube.transform.localRotation = Quaternion.Euler(0f, 20f, 0f);
            SetStatus("Rotate 20 degrees and update rig");
            yield return WaitForAdvance();

            bounds.EnabledHandles = HandleType.None;
            SetStatus("HandleType None");
            yield return WaitForAdvance();

            bounds.EnabledHandles = HandleType.Rotation;
            SetStatus("HandleType Rotation");
            yield return WaitForAdvance();

            bounds.EnabledHandles = HandleType.Scale;
            SetStatus("HandleType Scale");
            yield return WaitForAdvance();

            bounds.EnabledHandles = HandleType.Translation;
            SetStatus("HandleType Translation");
            yield return WaitForAdvance();

            Destroy(cube);
        }

        private IEnumerator MultiRootDemo()
        {
            GameObject multiRoot = new GameObject("multiRoot");
            Vector3 offset = Vector3.forward * 0.5f;
            multiRoot.transform.position = basePosition + offset;

            Transform lastParent = null;
            for (int i = 0; i < 10; i++)
            {
                var childCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                childCube.GetComponent<MeshRenderer>().material = cubeMaterial;
                childCube.transform.localPosition = Random.insideUnitSphere + basePosition + offset;
                childCube.transform.rotation = Quaternion.Euler(Random.insideUnitSphere * 360f);
                childCube.transform.parent = lastParent == null ? multiRoot.transform : lastParent;
                float baseScale = lastParent == null ? 0.1f : 1f;
                childCube.transform.localScale = Vector3.one * baseScale;
                lastParent = childCube.transform;
            }

            BoundsControl bounds = SetupBoundsControl(multiRoot);

            SetStatus("Many children");
            yield return WaitForAdvance();

            SetStatus("Randomize Child Scale for skewing");
            multiRoot.transform.position += Vector3.forward * 200f;

            var node = multiRoot.transform;
            while (node.childCount > 0)
            {
                node = node.GetChild(0);
                float baseScale = lastParent == null ? 0.1f : 1f;
                node.localScale = new Vector3(
                    baseScale * Random.Range(0.5f, 2f),
                    baseScale * Random.Range(0.5f, 2f),
                    baseScale * Random.Range(0.5f, 2f));
            }

            bounds.RecomputeBounds();
            yield return WaitForAdvance();

            SetStatus("Delete GameObject");
            Destroy(multiRoot);
            yield return WaitForAdvance();

            SetStatus("Done!");
            yield return WaitForAdvance();
        }

        private BoundsControl SetupBoundsControl(GameObject target)
        {
            target.AddComponent<ConstraintManager>();
            target.AddComponent<ObjectManipulator>();
            var bc = target.AddComponent<BoundsControl>();
            bc.BoundsVisualsPrefab = boundsVisualsPrefab;
            bc.HandlesActive = true;
            bc.DragToggleThreshold = 0.02f;
            target.AddComponent<UGUIInputAdapterDraggable>();
            return bc;
        }

        public void OnShouldAdvanceSequence()
        {
            advance = true;
        }
    }
}
