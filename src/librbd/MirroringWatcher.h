// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab

#ifndef CEPH_LIBRBD_MIRRORING_WATCHER_H
#define CEPH_LIBRBD_MIRRORING_WATCHER_H

#include "include/int_types.h"
#include "include/rados/librados.hpp"
#include "cls/rbd/cls_rbd_types.h"
#include "librbd/ImageCtx.h"
#include "librbd/ObjectWatcher.h"
#include "librbd/mirroring_watcher/Types.h"

namespace librbd {

template <typename ImageCtxT = librbd::ImageCtx>
class MirroringWatcher : public ObjectWatcher<ImageCtxT> {
public:
  typedef typename std::decay<decltype(*ImageCtxT::op_work_queue)>::type ContextWQT;

  MirroringWatcher(librados::IoCtx &io_ctx, ContextWQT *work_queue);

  static int notify_mode_updated(librados::IoCtx &io_ctx,
                                 cls::rbd::MirrorMode mirror_mode);
  static int notify_image_updated(librados::IoCtx &io_ctx,
                                  cls::rbd::MirrorImageState mirror_image_state,
                                  const std::string &image_id,
                                  const std::string &global_image_id);

protected:
  virtual std::string get_oid() const;

private:

};

} // namespace librbd

extern template class librbd::MirroringWatcher<librbd::ImageCtx>;

#endif // CEPH_LIBRBD_MIRRORING_WATCHER_H
