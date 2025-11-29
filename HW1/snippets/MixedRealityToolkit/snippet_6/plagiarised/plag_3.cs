using MixedReality.Toolkit.SpatialManipulation;
using MixedReality.Toolkit.UX;
using System.Collections;
using System.Text;
using TMPro;
using UnityEngine;

namespace MixedReality.Toolkit.Examples.Demos
{
    public class BoundsControlRuntimeWalkthrough : MonoBehaviour
    {
        [SerializeField]
        private TextMeshPro statusDisplay;

        [SerializeField]
        private Material defaultCubeMaterial;

        [SerializeField]
        private GameObject boundsVisualsPrefab;

        [SerializeField]
        private Transform cubeRoot;

        private bool nextRequested;
        private readonly Vector3 startPosition = new Vector3(0, 1.2f, 2);
        private readonly Vector3 startSize = new Vector3(0.5f, 0.5f, 0.5f);
        private BoundsControl demoBounds;
        private readonly StringBuilder textBuilder = new StringBuilder();

        private void Start()
        {
            StartCoroutine(Sequence());
        }

        private void SetStatus(string text)
        {
            Debug.Assert(statusDisplay != null, "statusDisplay must be assigned.");
            textBuilder.Clear();
            textBuilder.AppendLine(text);
            textBuilder.AppendLine("Press Next (or say 'next') to continue...");
            statusDisplay.text = textBuilder.ToString();
        }

        private GameObject CreateDemoCube()
        {
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.GetComponent<MeshRenderer>().material = defaultCubeMaterial;
            cube.transform.SetParent(cubeRoot == null ? transform : cubeRoot);
            cube.transform.position = startPosition;
            cube.transform.localScale = startSize;
            return cube;
        }

        private IEnumerator Sequence()
        {
            while (true)
            {
                var cube = CreateDemoCube();

                SetStatus("Instantiate BoundsControl");
                demoBounds = InitializeBounds(cube);
                yield return WaitForStep();

                SetStatus("Set Target bounds override");
                var overrideContainer = new GameObject("OverrideBounds");
                overrideContainer.transform.position = new Vector3(0.8f, 0.8f, 1.8f);
                var overrideCollider = overrideContainer.AddComponent<BoxCollider>();
                overrideCollider.size = new Vector3(0.162f, 0.1f, 1f);
                demoBounds.OverrideBounds = true;
                demoBounds.BoundsOverride = overrideCollider.transform;
                yield return WaitForStep();

                SetStatus("Change target bounds override size");
                overrideCollider.size = new Vector3(0.5f, 0.1f, 1f);
                demoBounds.RecomputeBounds();
                yield return WaitForStep();

                SetStatus("RotateAnchor Object Origin");
                demoBounds.RotateAnchor = RotateAnchorType.ObjectOrigin;
                yield return WaitForStep();

                SetStatus("RotateAnchor Bounds Center");
                demoBounds.RotateAnchor = RotateAnchorType.BoundsCenter;
                yield return WaitForStep();

                SetStatus("ScaleAnchor Opposite Corner");
                demoBounds.ScaleAnchor = ScaleAnchorType.OppositeCorner;
                yield return WaitForStep();

                SetStatus("ScaleAnchor Bounds Center");
                demoBounds.ScaleAnchor = ScaleAnchorType.BoundsCenter;
                yield return WaitForStep();

                SetStatus("Remove target bounds override");
                demoBounds.OverrideBounds = false;
                demoBounds.BoundsOverride = null;
                Destroy(overrideContainer);
                yield return WaitForStep();

                SetStatus("FlattenAuto");
                demoBounds.FlattenMode = FlattenMode.Auto;
                yield return WaitForStep();

                SetStatus("FlattenAlways");
                demoBounds.FlattenMode = FlattenMode.Always;
                yield return WaitForStep();

                SetStatus("FlattenNever");
                demoBounds.FlattenMode = FlattenMode.Never;
                yield return WaitForStep();

                SetStatus("BoxPadding 0.2f");
                demoBounds.BoundsPadding = 0.2f;
                yield return WaitForStep();

                SetStatus("BoxPadding 0");
                demoBounds.BoundsPadding = 0f;
                yield return WaitForStep();

                SetStatus("Scale X and update rig");
                cube.transform.localScale = new Vector3(1f, 0.5f, 0.5f);
                yield return WaitForStep();

                SetStatus("Rotate 20 degrees and update rig");
                cube.transform.localRotation = Quaternion.Euler(0f, 20f, 0f);
                yield return WaitForStep();

                SetStatus("HandleType None");
                demoBounds.EnabledHandles = HandleType.None;
                yield return WaitForStep();

                SetStatus("HandleType Rotation");
                demoBounds.EnabledHandles = HandleType.Rotation;
                yield return WaitForStep();

                SetStatus("HandleType Scale");
                demoBounds.EnabledHandles = HandleType.Scale;
                yield return WaitForStep();

                SetStatus("HandleType Translation");
                demoBounds.EnabledHandles = HandleType.Translation;
                yield return WaitForStep();

                Destroy(cube);

                SetStatus("Many children");
                GameObject multiRoot = new GameObject("multiRoot");
                Vector3 forwardOffset = Vector3.forward * 0.5f;
                multiRoot.transform.position = startPosition + forwardOffset;

                Transform parentChain = null;
                const int count = 10;

                for (int i = 0; i < count; i++)
                {
                    var childCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    childCube.GetComponent<MeshRenderer>().material = defaultCubeMaterial;
                    childCube.transform.localPosition = Random.insideUnitSphere + startPosition + forwardOffset;
                    childCube.transform.rotation = Quaternion.Euler(Random.insideUnitSphere * 360f);
                    childCube.transform.parent = parentChain == null ? multiRoot.transform : parentChain;
                    float baseScale = parentChain == null ? 0.1f : 1f;
                    childCube.transform.localScale = Vector3.one * baseScale;
                    parentChain = childCube.transform;
                }

                demoBounds = InitializeBounds(multiRoot);

                SetStatus("Randomize Child Scale for skewing");
                yield return WaitForStep();

                multiRoot.transform.position += Vector3.forward * 200f;

                var node = multiRoot.transform;
                while (node.childCount > 0)
                {
                    node = node.GetChild(0);
                    float baseScale = parentChain == null ? 0.1f : 1f;
                    node.localScale = new Vector3(
                        baseScale * Random.Range(0.5f, 2f),
                        baseScale * Random.Range(0.5f, 2f),
                        baseScale * Random.Range(0.5f, 2f));
                }

                demoBounds.RecomputeBounds();

                SetStatus("Delete GameObject");
                yield return WaitForStep();

                Destroy(multiRoot);

                SetStatus("Done!");
                yield return WaitForStep();
            }
        }

        private BoundsControl InitializeBounds(GameObject target)
        {
            target.AddComponent<ConstraintManager>();
            target.AddComponent<ObjectManipulator>();
            var bounds = target.AddComponent<BoundsControl>();
            bounds.BoundsVisualsPrefab = boundsVisualsPrefab;
            bounds.HandlesActive = true;
            bounds.DragToggleThreshold = 0.02f;
            target.AddComponent<UGUIInputAdapterDraggable>();
            return bounds;
        }

        private IEnumerator WaitForStep()
        {
            while (!nextRequested)
            {
                yield return null;
            }

            nextRequested = false;
        }

        public void OnShouldAdvanceSequence()
        {
            nextRequested = true;
        }
    }
}
